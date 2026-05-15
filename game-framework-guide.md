# Unity Game Framework (UGF) 完整架构指南

## 一、整体架构概览

Game Framework 采用**双层架构**：

```
┌─────────────────────────────────────────────────┐
│  Unity Game Framework (UGF) — Unity 适配层       │
│  Scripts/Runtime/ — 各模块 Component 类             │
│  GameFrameworkComponent : MonoBehaviour           │
│  GameEntry, UIForm, UIFormLogic 等                 │
├─────────────────────────────────────────────────┤
│  Game Framework — 核心框架层                        │
│  GameFramework/ — 纯 C# 实现，与引擎无关             │
│  GameFrameworkEntry / GameFrameworkModule          │
│  UIManager / IUIManager / IUIForm 等               │
└─────────────────────────────────────────────────┘
```

### 双层职责划分

| 层级 | 职责 | 典型类 |
|------|------|---------|
| 核心层 (GameFramework) | 纯 C# 游戏框架，与引擎无关，实现各模块的业务逻辑 | `GameFrameworkModule`, `GameFrameworkEntry`, 各 Manager |
| Unity 适配层 (UGF) | 将核心层桥接到 Unity 引擎 | `GameFrameworkComponent`, `GameEntry`, `UIForm`, `UIFormLogic` |

---

## 二、核心层 (GameFramework) 模块总览

核心层包含 **21 个模块**，每个模块由三部分组成：

```
模块名/
├── I{Module}Manager.cs   — 接口（如 IEntityManager）
├── {Module}Manager.cs     — 实现类（如 EntityManager）
└── 相关事件/辅助接口       — EventArgs, Helper 等
```

| 序号 | 模块名 | 接口 | 实现类 | 职责 |
|------|--------|------|--------|------|
| 1 | Base | — | GameFrameworkEntry / GameFrameworkModule | 基础架构，模块注册与轮询 |
| 2 | Config | IConfigManager / IConfigHelper | ConfigManager | 配置文件管理（XML/JSON 等） |
| 3 | DataNode | IDataNodeManager / IDataNode | DataNodeManager | 数据节点（树形结构数据） |
| 4 | DataTable | IDataTableManager / IDataTable / IDataRow | DataTableManager | 数据表管理（Excel/CSV 导入） |
| 5 | Debugger | IDebuggerManager / IDebuggerWindow | DebuggerManager | 调试器与调试窗口 |
| 6 | Download | IDownloadManager / IDownloadAgentHelper | DownloadManager | 文件下载（进度、重试、断点） |
| 7 | Entity | IEntityManager / IEntity / IEntityGroup / IEntityHelper | EntityManager | 实体系统（显示/隐藏/回收） |
| 8 | Event | IEventManager | EventManager | 事件总线（发布/订阅模式） |
| 9 | FileSystem | IFileSystemManager / IFileSystem / IFileSystemHelper | FileSystemManager | 虚拟文件系统 |
| 10 | Fsm | IFsmManager / IFsm / IFsmState | FsmManager | 有限状态机 |
| 11 | Localization | ILocalizationManager / ILocalizationHelper | LocalizationManager | 多语言本地化 |
| 12 | Network | INetworkManager / INetworkChannel | NetworkManager | 网络通信（TCP、心跳、重连） |
| 13 | ObjectPool | IObjectPoolManager / IObjectPool / ObjectBase | ObjectPoolManager | 对象池（实例复用） |
| 14 | Procedure | IProcedureManager / ProcedureBase | ProcedureManager | 流程控制（状态化流程编排） |
| 15 | Resource | IResourceManager / IResourceHelper / IResourceGroup | ResourceManager | 资源加载/卸载/版本管理 |
| 16 | Scene | ISceneManager | SceneManager | 场景管理 |
| 17 | Setting | ISettingManager / ISettingHelper | SettingManager | 游戏设置持久化 |
| 18 | Sound | ISoundManager / ISoundAgent / ISoundGroup | SoundManager | 声音系统（播放/停止/混音） |
| 19 | UI | IUIManager / IUIForm / IUIGroup | UIManager | 界面管理 |
| 20 | Utility | — | Utility (多个子模块) | 工具类（日志、JSON、压缩、文本等） |
| 21 | WebRequest | IWebRequestManager / IWebRequestAgentHelper | WebRequestManager | HTTP 请求 |

---

## 三、核心架构类详解

### 3.1 GameFrameworkModule — 模块基类

```csharp
internal abstract class GameFrameworkModule
{
    internal virtual int Priority { get; }       // 优先级，决定轮询顺序
    internal abstract void Update(float elapseSeconds, float realElapseSeconds);
    internal abstract void Shutdown();
}
```

**职责**：
- 所有框架模块的抽象基类
- `Priority` 决定模块在 Update 链表中的排序（优先级高的先执行）
- 每个具体模块（如 `UIManager`、`EntityManager`）都继承此基类

### 3.2 GameFrameworkEntry — 框架入口

```csharp
public static class GameFrameworkEntry
{
    // 模块链表，按 Priority 排序
    private static readonly GameFrameworkLinkedList<GameFrameworkModule> s_GameFrameworkModules;

    // 轮询所有模块
    public static void Update(float elapseSeconds, float realElapseSeconds);

    // 关闭所有模块
    public static void Shutdown();

    // 获取模块（通过接口名自动查找并懒加载）
    public static T GetModule<T>() where T : class;
}
```

**工作原理**：
- `GetModule<IUIManager>()` → 拼接类名 `GameFramework.UI.UIManager` → 自动 `Activator.CreateInstance`
- `Update()` 遍历所有模块调用各自的 `Update()` 方法
- `Shutdown()` 逆序关闭所有模块，清理 ReferencePool 等资源

### 3.3 GameFrameworkLinkedList — 自定义双向链表

```csharp
internal class GameFrameworkLinkedList<T>
{
    // 自定义链表实现，用于模块/组件的顺序管理
    // 支持 AddFirst, AddLast, AddBefore, Clear, 遍历等
}
```

### 3.4 GameFrameworkLog — 日志系统

```csharp
internal static class GameFrameworkLog
{
    internal static void SetLogHelper(ILogHelper logHelper);
    internal static void Trace(...);
    internal static void Debug(...);
    internal static void Info(...);
    internal static void Warning(...);
    internal static void Error(...);
    internal static void Fatal(...);
}
```

---

## 四、UI 系统架构

UI 系统是 UGF 中最重要的子系统，结构最为复杂。

### 4.1 架构总览

```
GameFramework (核心层)                    UnityGameFramework (适配层)
┌─────────────────────┐                  ┌──────────────────────────┐
│ IUIManager           │── 接口 ──→      │ UIComponent              │
│ UIManager            │── 实现 ──→      │ 封装 IUIManager 调用       │
│ IUIForm              │── 接口 ──→      │ UIForm : MonoBehaviour   │
│ IUIFormHelper        │── 接口 ──→      │ UIFormHelperBase           │
│ IUIFormHelper        │── 接口 ──→      │ DefaultUIFormHelper        │
│ IUIGroup              │── 接口 ──→      │ UIGroupHelperBase          │
│ IUIGroupHelper        │── 接口 ──→      │ DefaultUIGroupHelper       │
└─────────────────────┘                  └──────────────────────────┘
```

### 4.2 UIManager (核心层) 完整接口

`UIManager` 继承 `GameFrameworkModule` 并实现 `IUIManager` 接口：

```csharp
internal sealed partial class UIManager : GameFrameworkModule, IUIManager
```

**核心数据结构**：
- `m_UIGroups` — Dictionary<string, UIGroup> 存储所有界面组
- `m_UIFormsBeingLoaded` — Dictionary<int, string> 追踪正在加载的界面
- `m_InstancePool` — ObjectPool<UIFormInstanceObject> 界面实例对象池

**IUIManager 接口核心方法**：

| 方法分类 | 方法 | 说明 |
|-----------|------|------|
| 界面组管理 | `HasUIGroup(uiGroupName)` | 检查界面组是否存在 |
| 界面组管理 | `GetUIGroup(uiGroupName)` | 获取指定界面组 |
| 界面组管理 | `AddUIGroup(name, depth, helper)` | 创建新界面组 |
| 界面查询 | `HasUIForm(serialId / assetName)` | 检查界面是否存在 |
| 界面查询 | `GetUIForm(serialId / assetName)` | 获取界面引用 |
| 界面查询 | `GetAllLoadedUIForms()` | 获取所有已加载的界面 |
| 界面查询 | `GetAllLoadingUIFormSerialIds()` | 获取正在加载的界面序列号 |
| 界面操作 | `OpenUIForm(assetName, groupName, ...)` | 打开界面，返回序列号 |
| 界面操作 | `CloseUIForm(serialId / uiForm)` | 关闭界面 |
| 界面操作 | `RefocusUIForm(uiForm)` | 激活指定界面 |
| 对象池配置 | `InstanceAutoReleaseInterval` | 自动释放间隔（秒） |
| 对象池配置 | `InstanceCapacity` | 对象池容量 |
| 对象池配置 | `InstanceExpireTime` | 实例过期时间（秒） |
| 依赖设置 | `SetResourceManager(ResourceManager)` | 设置资源管理器 |
| 依赖设置 | `SetObjectPoolManager(ObjectPoolManager)` | 设置对象池管理器 |
| 依赖设置 | `SetUIFormHelper(UIFormHelper)` | 设置界面辅助器 |

**事件（EventHandler）**：
- `OpenUIFormSuccess` — 界面打开成功
- `OpenUIFormFailure` — 界面打开失败
- `OpenUIFormUpdate` — 界面加载进度更新
- `OpenUIFormDependencyAsset` — 加载依赖资源时触发
- `CloseUIFormComplete` — 界面关闭完成

### 4.3 IUIForm — 界面接口

```csharp
public interface IUIForm
{
    int SerialId { get; }                    // 界面序列编号
    string UIFormAssetName { get; }           // 资源名称
    object Handle { get; }                    // 界面实例引用
    IUIGroup UIGroup { get; }                // 所属界面组
    int DepthInUIGroup { get; }             // 在界面组中的深度
    bool PauseCoveredUIForm { get; }         // 是否暂停被覆盖的界面

    // 生命周期回调
    void OnInit(int serialId, string uiFormAssetName, IUIGroup uiGroup, bool pauseCoveredUIForm, bool isNewInstance, object userData);
    void OnRecycle();
    void OnOpen(object userData);
    void OnClose(bool isShutdown, object userData);
    void OnPause();
    void OnResume();
    void OnCover();
    void OnReveal();
    void OnRefocus(object userData);
    void OnUpdate(float elapseSeconds, float realElapseSeconds);
    void OnDepthChanged(int uiGroupDepth, int depthInUIGroup);
}
```

### 4.4 UIForm (UGF 层) — 界面实现

```csharp
public sealed class UIForm : MonoBehaviour, IUIForm
{
    private UIFormLogic m_UIFormLogic;

    // IUIForm 接口实现
    public int SerialId { get; }
    public string UIFormAssetName { get; }
    public object Handle { get; }    // 返回 gameObject
    public IUIGroup UIGroup { get; }
    public int DepthInUIGroup { get; }
    public bool PauseCoveredUIForm { get; }
    public UIFormLogic Logic { get; }

    // Unity 生命周期
    private void Awake()  { /* 绑定 IUIForm 属性 */ }
    private void Update() { OnUpdate(Time.deltaTime, Time.unscaledDeltaTime); }
    private void OnDestroy() { /* 回收 */ }
}
```

**UIForm 与 IUIForm 的映射**：
- `Handle` 属性返回 `gameObject`（Unity GameObject 作为界面实例）
- `Logic` 属性返回 `UIFormLogic` 实例（业务逻辑层）

### 4.5 UIFormLogic — 界面业务逻辑基类

```csharp
public abstract class UIFormLogic : UIFormLogicBase
{
    // 提供对 UIForm 的引用
    public UIForm UIForm { get; }
    // 子界面引用管理
    protected T GetUIForm<T>(string uiFormAssetName);
}
```

**UIFormLogic 的生命周期方法**（子类可重写）：

| 方法 | 触发时机 | 用途 |
|------|----------|------|
| `OnInit` | 界面首次创建或从对象池取出时 | 初始化 UI 控件绑定 |
| `OnOpen` | 界面被打开时 | 显示界面、设置数据 |
| `OnClose` | 界面被关闭时 | 清理、保存数据 |
| `OnRecycle` | 界面被回收至对象池时 | 重置状态 |
| `OnPause` | 界面被覆盖（新界面弹出） | 暂停逻辑 |
| `OnResume` | 界面从暂停恢复 | 恢复逻辑 |
| `OnCover` | 被新界面覆盖 | 失去焦点 |
| `OnReveal` | 覆盖层移除 | 恢复焦点 |
| `OnRefocus` | 手动激活界面 | 重新聚焦 |
| `OnUpdate` | 每帧调用 | 持续更新逻辑 |

**典型使用方式**：
```csharp
public class UIMyPanelLogic : UIFormLogic
{
    private Button m_BtnSubmit;
    private Text m_TextInfo;

    public override void OnInit(object userData)
    {
        // 绑定 UI 组件（通常由工具自动生成）
        m_BtnSubmit = this.transform.Find("BtnSubmit").GetComponent<Button>();
        m_BtnSubmit.onClick += OnSubmitClicked;
    }

    public override void OnOpen(object userData)
    {
        // 打开界面时处理
    }
}
```

### 4.6 UIFormHelper — 界面辅助器

**核心层接口**：
```csharp
public interface IUIFormHelper
{
    object InstantiateUIForm(object uiFormAsset);
    IUIForm CreateUIForm(object uiFormInstance, IUIGroup uiGroup, object userData);
    void ReleaseUIForm(object uiFormAsset, object uiFormInstance);
}
```

**UGF 层的实现**：
```csharp
public class UIFormHelperBase : MonoBehaviour, IUIFormHelper { ... }
public class DefaultUIFormHelper : UIFormHelperBase
{
    // 实例化：从资源创建 GameObject
    public override object InstantiateUIForm(object uiFormAsset)
    {
        return Instantiate((Object)uiFormAsset);
    }

    // 创建：将 GameObject 附加 UIForm 组件
    public override IUIForm CreateUIForm(object uiFormInstance, IUIGroup uiGroup, object userData)
    {
        GameObject go = uiFormInstance as GameObject;
        // 设置父节点
        go.transform.SetParent(((MonoBehaviour)uiGroup.Helper).transform);
        return go.GetOrAddComponent<UIForm>();
    }

    // 释放：卸载资源并销毁 GameObject
    public override void ReleaseUIForm(object uiFormAsset, object uiFormInstance)
    {
        m_ResourceComponent.UnloadAsset(uiFormAsset);
        Destroy((Object)uiFormInstance);
    }
}
```

---

## 五、UGF 适配层 — GameFrameworkComponent 桥梁

### 5.1 GameFrameworkComponent — 核心桥梁类

```csharp
public abstract class GameFrameworkComponent : MonoBehaviour
{
    protected virtual void Awake()
    {
        GameEntry.RegisterComponent(this);
    }
}
```

**工作原理**：
1. 所有 UGF Component 继承 `GameFrameworkComponent`
2. `Awake()` 自动调用 `GameEntry.RegisterComponent(this)` 注册到全局链表
3. 在 `BaseComponent.Update()` 中调用 `GameFrameworkEntry.Update()` 轮询所有核心模块

### 5.2 GameEntry — 组件管理中心

```csharp
public static class GameEntry
{
    // 注册所有 GameFrameworkComponent 到链表
    internal static void RegisterComponent(GameFrameworkComponent component);

    // 通过类型获取组件
    public static T GetComponent<T>() where T : GameFrameworkComponent;
    public static GameFrameworkComponent GetComponent(Type type);
    public static GameFrameworkComponent GetComponent(string typeName);

    // 关闭
    public static void Shutdown(ShutdownType shutdownType);
}
```

### 5.3 BaseComponent — 基础组件

```csharp
public sealed class BaseComponent : GameFrameworkComponent
{
    // Unity 生命周期桥接
    private void Update()
    {
        GameFrameworkEntry.Update(Time.deltaTime, Time.unscaledDeltaTime);
    }

    private void OnDestroy()
    {
        GameFrameworkEntry.Shutdown();
    }

    // 配置初始化（TextHelper, LogHelper, JsonHelper 等）
    private void InitTextHelper();
    private void InitVersionHelper();
    private void InitLogHelper();
    private void InitCompressionHelper();
    private void InitJsonHelper();
}
```

---

## 六、所有 UGF Runtime 组件总览

每个模块在 UGF 层都有一个对应的 `*Component` 类：

| UGF Component | 对应核心层模块 | 核心层 Manager | 核心层接口 |
|---------------|----------------|----------------|-----------|
| `BaseComponent` | Base | — | — |
| `ConfigComponent` | Config | ConfigManager | IConfigManager / IConfigHelper |
| `DataNodeComponent` | DataNode | DataNodeManager | IDataNodeManager / IDataNode |
| `DataTableComponent` | DataTable | DataTableManager | IDataTableManager / IDataTable / IDataRow |
| `DebuggerComponent` | Debugger | DebuggerManager | IDebuggerManager / IDebuggerWindow |
| `DownloadComponent` | Download | DownloadManager | IDownloadManager / IDownloadAgentHelper |
| `EntityComponent` | Entity | EntityManager | IEntityManager / IEntity / IEntityGroup / IEntityHelper |
| `EventComponent` | Event | EventManager | IEventManager |
| `FileSystemComponent` | FileSystem | FileSystemManager | IFileSystemManager / IFileSystem / IFileSystemHelper |
| `FsmComponent` | Fsm | FsmManager | IFsmManager / IFsm |
| `LocalizationComponent` | Localization | LocalizationManager | ILocalizationManager / ILocalizationHelper |
| `NetworkComponent` | Network | NetworkManager | INetworkManager / INetworkChannel |
| `ObjectPoolComponent` | ObjectPool | ObjectPoolManager | IObjectPoolManager / IObjectPool |
| `ProcedureComponent` | Procedure | ProcedureManager | IProcedureManager |
| `ResourceComponent` | Resource | ResourceManager | IResourceManager / IResourceHelper / IResourceGroup |
| `SceneComponent` | Scene | SceneManager | ISceneManager |
| `SettingComponent` | Setting | SettingManager | ISettingManager / ISettingHelper |
| `SoundComponent` | Sound | SoundManager | ISoundManager / ISoundAgent / ISoundGroup |
| `UIComponent` | UI | UIManager | IUIManager / IUIForm / IUIGroup |
| `WebRequestComponent` | WebRequest | WebRequestManager | IWebRequestManager / IWebRequestAgentHelper |

---

## 七、数据流与生命周期

### 7.1 模块初始化流程

```
GameEntry (UGF)
  ↓ RegisterComponent(this) in each Component's Awake()

BaseComponent.Update()
  ↓ GameFrameworkEntry.Update(deltaTime, unscaledDeltaTime)

GameFrameworkEntry.Update()
  ↓ 遍历 s_GameFrameworkModules
  → 调用每个 module.Update()

各 Manager.Update()
  → 处理各自模块的逻辑（资源加载、网络通信、UI 更新等）
```

### 7.2 UI 界面打开流程

```
UIComponent.OpenUIForm(assetName, groupName)
  ↓
UIManager.OpenUIForm()  [核心层]
  → 检查是否已存在 / 正在加载
  → 从 Resource 加载 UI 预设资源
  → UIFormHelper.InstantiateUIForm() 创建 GameObject
  → UIFormHelper.CreateUIForm() 附加 UIForm 组件
  → UIForm.OnInit() 初始化
  → UIForm.OnOpen() 打开界面
  → 触发 OpenUIFormSuccess 事件
```

### 7.3 UI 界面关闭流程

```
UIComponent.CloseUIForm(serialId)
  ↓
UIManager.CloseUIForm()  [核心层]
  → UIForm.OnClose() 关闭
  → UIForm.OnRecycle() 回收
  → UIFormHelper.ReleaseUIForm() 释放资源
  → 触发 CloseUIFormComplete 事件
```

---

## 八、快速参考 — 核心接口速查

| 接口 | 所属层 | 用途 |
|------|---------|------|
| `GameFrameworkModule` | 核心层 | 所有模块的抽象基类 |
| `GameFrameworkEntry` | 核心层 | 框架入口，模块注册与轮询 |
| `GameFrameworkComponent` | UGF 层 | MonoBehaviour 桥梁类 |
| `GameEntry` | UGF 层 | 组件管理中心 |
| `IUIManager` | 核心层 | 界面管理器接口 |
| `UIManager` | 核心层 | 界面管理器实现 |
| `IUIForm` | 核心层 | 界面接口（生命周期回调） |
| `UIForm` | UGF 层 | 界面实现（继承 MonoBehaviour） |
| `UIFormLogic` | UGF 层 | 界面业务逻辑基类 |
| `IUIFormHelper` | 核心层 | 界面辅助器接口（实例化/创建/释放） |
| `UIFormHelperBase` | UGF 层 | 界面辅助器基类（继承 MonoBehaviour） |
| `DefaultUIFormHelper` | UGF 层 | 默认界面辅助器实现 |

---

## 九、常见使用模式

### 获取模块

```csharp
// 核心层方式（纯 C#）
IUIManager uiManager = GameFrameworkEntry.GetModule<IUIManager>();

// UGF 层方式（通过 GameEntry 获取组件）
UIComponent uiComponent = GameEntry.GetComponent<UIComponent>();
```

### 打开/关闭界面

```csharp
UIComponent ui = GameEntry.GetComponent<UIComponent>();

// 打开界面
int serialId = ui.OpenUIForm("UI/MainPanel", "Default");

// 关闭界面
ui.CloseUIForm(serialId);

// 获取已打开的界面
UIForm form = ui.GetUIForm("UI/MainPanel");
if (form != null)
{
    // 通过 Logic 访问业务逻辑
    var logic = form.Logic as MyPanelLogic;
}
```

### 创建自定义 UIFormLogic

```csharp
public class MyPanelLogic : UIFormLogic
{
    // 在 Unity 编辑器中绑定 UI 组件
    public Button m_BtnOK;
    public Text m_TextTitle;

    public override void OnInit(object userData)
    {
        // 初始化逻辑
    }

    public override void OnOpen(object userData)
    {
        // 打开时执行
    }

    public override void OnClose(bool isShutdown, object userData)
    {
        // 关闭时执行
    }
}
```

---

## 十、注意事项

1. **接口获取模块**：`GameFrameworkEntry.GetModule<T>()` 要求 `T` 必须是接口类型（`I*Manager`），不能传具体类
2. **模块优先级**：`GameFrameworkModule.Priority` 决定 Update 执行顺序，优先级高的先执行
3. **UI 对象池**：`InstanceCapacity` 控制对象池容量，合理设置可减少 GC
4. **Helper 模式**：所有 Helper 接口（`I*Helper`）采用**策略模式**，允许自定义实现（如 `IConfigHelper` 可切换 XML/JSON/CSV 解析器）
5. **双层解耦**：核心层完全不依赖 Unity，可移植到其他引擎；UGF 层负责 Unity 引擎适配
6. **Event 系统**：`IEventManager` 实现发布/订阅模式，用于模块间解耦通信
7. **Resource 版本管理**：`ResourceManager` 支持版本列表（VersionList）实现热更新和增量下载