# UnityGameFramework 详细指南


**📊 配套资源**：架构思维导图（SVG）→ `~/.hermes/notes/UnityGameFramework_Architecture.html`（用浏览器打开查看）

> **UnityGameFramework**（简称 UGF）是一个基于 Unity 引擎的游戏框架，对游戏开发常用模块进行了封装，规范开发过程、加快开发速度并保证产品质量。
 **Demo**: https://github.com/EllanJiang/StarForce ⭐966

---

## 目录

1. [架构总览](#1-架构总览)
2. [核心类层次结构](#2-核心类层次结构)
3. [MonoBehaviour 集成机制](#3-monobehavior-集成机制)
4. [19 个内置模块详解](#4-19-个内置模块详解)
5. [UI 系统：IUIForm → UIForm 链路](#5-ui-系统-iuiform--uiform-链路)
6. [GameFramework 与 Unity UI 组件的链接](#6-gameframework-与-unity-ui-组件的链接)
7. [StarForce Demo 实例分析](#7-starforce-demo-实例分析)
8. [开发最佳实践](#8-开发最佳实践)
9. [常见问题](#9-常见问题)

---

## 1. 架构总览

### 1.1 架构设计哲学

```
┌─────────────────────────────────────────────────────────────┐
│                    GameEntry (入口点)                          │
│  └── 管理所有 Component 的初始化、启动、更新、释放生命周期        │
└─────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│              GameFrameworkComponent (核心组件基类)                │
│  └── 继承自 BaseComponent，提供框架级别的组件管理                   │
│      └── GetComponent() 通过组件名获取对应组件                      │
└─────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│              BaseComponent (基础组件基类)                           │
│  └── 提供 OnAwake / OnStart / OnUpdate / OnDispose 生命周期       │
└─────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│         各功能组件 (Component)                                   │
│  └── ConfigComponent, UIComponent, EntityComponent 等            │
│      │                                                           │
│      ▼                                                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  各功能管理器 (Manager)                                     │  │
│  │  └── ConfigManager, UIManager, EntityManager 等            │  │
│  │      │                                                       │  │
│  │      ▼                                                       │  │
│  │  ┌──────────────────────────────────────────────────────┐  │  │
│  │  │  各功能助手类 (Helper)                                    │  │
│  │  │  └── 可替换的实现类，用于定制化行为                           │  │
│  │  └──────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**三层架构模式**：
- **Component 层**：面向 Unity GameObject 的入口，管理 Manager 的生命周期
- **Manager 层**：核心业务逻辑，处理模块的具体功能
- **Helper 层**：可替换的实现细节，便于扩展和定制

### 1.2 项目目录结构

```
UnityGameFramework/
├── Scripts/
│   ├── Editor/          # Unity 编辑器扩展
│   └── Runtime/
│       ├── Base/         # 核心基类 (GameEntry, BaseComponent, GameFrameworkComponent)
│       ├── Config/       # 配置管理
│       ├── DataNode/     # 树状数据节点
│       ├── DataTable/    # 数据表管理
│       ├── Debugger/     # 调试器
│       ├── Download/     # 下载模块
│       ├── Entity/       # 实体管理
│       ├── Event/        # 事件系统
│       ├── FileSystem/    # 虚拟文件系统
│       ├── Fsm/          # 有限状态机
│       ├── Localization/  # 本地化
│       ├── Network/      # 网络模块
│       ├── ObjectPool/    # 对象池
│       ├── Procedure/     # 流程管理
│       ├── ReferencePool/ # 资源引用池
│       ├── Resource/      # 资源管理
│       ├── Scene/        # 场景管理
│       ├── Setting/       # 设置管理
│       ├── Sound/        # 音效管理
│       ├── UI/           # UI 系统
│       └── WebRequest/   # HTTP 请求
├── Libraries/            # 第三方库
├── GameFramework.prefab  # 框架预制体
└── package.json          # UPM 包配置
```

---

## 2. 核心类层次结构

### 2.1 GameEntry — 框架总入口

```csharp
// Scripts/Runtime/Base/GameEntry.cs
public static class GameEntry
{
    // 所有内置组件通过此方法注册到框架中
    public static GameFrameworkComponent GetComponent(string componentName);
    public static T GetComponent<T>() where T : GameFrameworkComponent;
    
    // 组件管理
    public static GameFrameworkComponent[] GetComponents();
    public static void AddComponent(GameFrameworkComponent component);
    
    // 框架配置
    public static GameFrameworkSettings Settings { get; }
    
    // 初始化与更新循环
    public static void Awake();
    public static void Start();
    public static void Update(float deltaTime);
    public static void Shutdown(ShutdownType shutdownType);
}
```

**作用**：作为整个框架的"中枢神经系统"，GameEntry 管理所有组件的生命周期。所有 GameFrameworkComponent 子类通过 GameEntry.AddComponent() 注册，随后 GameEntry.Update() 会调用每个组件的 OnUpdate()。

### 2.2 BaseComponent — 基础组件基类

```csharp
// Scripts/Runtime/Base/BaseComponent.cs
public abstract class BaseComponent
{
    // 生命周期回调
    protected virtual void OnAwake() { }
    protected virtual void OnStart() { }
    protected virtual void OnUpdate(float deltaTime) { }
    protected virtual void OnDispose() { }
    protected virtual void OnShutdown(ShutdownType shutdownType) { }
    
    // 名称
    public string Name { get; }
    public bool IsStarted { get; }
}
```

**作用**：定义所有组件共有的生命周期方法。框架调用这些方法来实现统一的组件管理。

### 2.3 GameFrameworkComponent — 核心组件基类

```csharp
// Scripts/Runtime/Base/GameFrameworkComponent.cs
public abstract class GameFrameworkComponent : BaseComponent
{
    // 获取子组件
    public T GetComponent<T>() where T : BaseComponent;
    
    // 注册/注销子组件
    public void AddComponent(BaseComponent component);
    public void RemoveComponent(BaseComponent component);
    
    // 内部组件集合
    public BaseComponent[] GetComponents();
}
```

**作用**：在 BaseComponent 基础上增加了子组件管理能力，是框架内各功能模块组件的基类。

---

## 3. MonoBehaviour 集成机制

UGF 通过 **GameFramework.prefab** 中的 MonoBehaviour 脚本将框架核心逻辑与 Unity 的生命周期桥接起来：

### 3.1 桥接关系

```
Unity 生命周期                    框架生命周期
─────────────────────────────────────────────────
MonoBehaviour.OnAwake() ──────► GameEntry.Awake()
MonoBehaviour.OnStart() ──────► GameEntry.Start()
MonoBehaviour.OnUpdate()  ─────► GameEntry.Update(Time.deltaTime)
MonoBehaviour.OnDisable() ─────► GameEntry.Shutdown()
```

### 3.2 GameFrameworkBehaviour

```csharp
// GameFrameworkBehaviour.cs (在 prefabs 中)
public class GameFrameworkBehaviour : MonoBehaviour
{
    // Unity 调用这些方法，桥接到 GameEntry
    private void Awake()  { GameEntry.Awake(); }
    private void Start()  { GameEntry.Start(); }
    private void Update() { GameEntry.Update(Time.deltaTime); }
    private void OnDestroy() { GameEntry.Shutdown(ShutdownType.ProcessExit); }
}
```

### 3.3 工作流程

1. **放置预制体**：将 `GameFramework.prefab` 拖入场景
2. **Awake 阶段**：`GameFrameworkBehaviour.Awake()` → `GameEntry.Awake()` → 所有组件 `OnAwake()`
3. **Start 阶段**：`GameEntry.Start()` → 所有组件 `OnStart()`
4. **Update 阶段**：每帧 `GameEntry.Update(deltaTime)` → 所有组件 `OnUpdate(deltaTime)`
5. **销毁阶段**：`GameEntry.Shutdown()` → 所有组件 `OnShutdown()` → `OnDispose()`

**要点**：MonoBehaviour 充当了 Unity 引擎和 GameFramework 之间的翻译官，让框架代码完全独立于 Unity 引擎。

---

## 4. 19 个内置模块详解

### 4.1 配置与数据模块

 模块 | 组件类 | 管理器类 | 核心接口 | 作用 |
------|---------|----------|----------|------|
 **Config** | ConfigComponent | ConfigManager | `IConfigData` | 存储全局只读游戏配置（初始速度、音量等） |
 **DataNode** | DataNodeComponent | DataNodeManager | `DataNode`, `IDataNode` | 以树状结构保存运行时数据 |
 **DataTable** | DataTableComponent | DataTableManager | `DataTable`, `DataRow` | 将 Excel 格式的数据表加载为游戏可用数据 |

### 4.2 调试与下载模块

 模块 | 组件类 | 管理器类 | 核心接口 | 作用 |
------|---------|----------|----------|------|
 **Debugger** | DebuggerComponent | DebuggerWindow | `IDebugger` | Development 模式下提供调试器窗口 |
 **Download** | DownloadComponent | DownloadManager | `IDownloadHandler` | 文件下载功能，支持断点续传、并发控制 |

### 4.3 实体与事件模块

 模块 | 组件类 | 管理器类 | 核心接口 | 作用 |
------|---------|----------|----------|------|
 **Entity** | EntityComponent | EntityManager | `IEntity`, `IEntityGroup` | 管理游戏场景中的动态物体（显示/隐藏/挂接） |
 **Event** | EventComponent | EventManager | `IEventCallback` | 游戏逻辑的事件监听与抛出机制 |

### 4.4 资源与场景模块

 模块 | 组件类 | 管理器类 | 核心接口 | 作用 |
------|---------|----------|----------|------|
 **FileSystem** | FileSystemComponent | FileSystemManager | `IFile`, `IFolder` | 虚拟文件系统，集中管理零散文件 |
 **Fsm** | FsmComponent | FsmManager | `IFsm`, `IFsmNode` | 有限状态机，管理游戏状态转换 |
 **Localization** | LocalizationComponent | LocalizationManager | `ILocalizationDictionary` | 多语言文本本地化 |
 **ObjectPool** | ObjectPoolComponent | ObjectPoolManager | `IPoolable` | 对象池，减少内存分配 |
 **ReferencePool** | ReferencePoolComponent | ReferencePoolManager | `IReference` | 资源引用池，管理资源加载状态 |
 **Resource** | ResourceComponent | ResourceManager | `IAsset` | 资源加载、缓存、释放 |
 **Scene** | SceneComponent | SceneManager | `IScene` | 场景加载、切换、卸载 |

### 4.5 网络与通信模块

 模块 | 组件类 | 管理器类 | 核心接口 | 作用 |
------|---------|----------|----------|------|
 **Network** | NetworkComponent | NetworkManager | `INetworkChannel` | 网络通信管理 |
 **WebRequest** | WebRequestComponent | WebRequestManager | `IWebRequest` | HTTP 请求管理 |

### 4.6 游戏逻辑与表现模块

 模块 | 组件类 | 管理器类 | 核心接口 | 作用 |
------|---------|----------|----------|------|
 **Procedure** | ProcedureComponent | ProcedureManager | `IProcedure` | 流程管理，组织游戏阶段（启动→菜单→游戏→结束） |
 **Setting** | SettingComponent | SettingManager | `ISetting` | 游戏设置持久化（分辨率、画质、音效等） |
 **Sound** | SoundComponent | SoundManager | `ISound` | 音效和音乐管理 |
 **UI** | UIComponent | UIManager | `IUIForm` | UI 界面管理（详见第5节） |

---

## 5. UI 系统：IUIForm → UIForm 链路

### 5.1 核心关系链

```
IUIForm (接口)
    │
    ▼
UIForm (实现类)
    │
    ▼
UIFormExtension (扩展类)
    │
    ▼
具体 UI 表单 (如 MainUIForm, MenuUIForm)
```

### 5.2 IUIForm 接口定义

```csharp
// Scripts/Runtime/UI/UIForm.cs
public interface IUIForm
{
    // 唯一标识
    string Name { get; }
    int UIFormType { get; }        // 0=独立窗口, 1=对话框, 2=覆盖层
    
    // 状态
    bool IsOpen { get; }
    float OpeningTime { get; }
    int OpeningProgress { get; }  // 0-100
    
    // 生命周期
    void Open();
    void Close();
    void Update(float deltaTime);
    void Dispose();
    
    // 事件
    event Action<IUIForm, object> OnOpen;
    event Action<IUIForm, object> OnClose;
}
```

### 5.3 UIForm 实现

```csharp
public abstract class UIForm : IUIForm
{
    // 从 UIComponent 获取
    protected UIComponent UI { get; }
    
    // 动画参数
    public virtual float AnimationDuration { get; }
    
    // 生命周期
    public virtual void OnOpen();
    public virtual void OnClose();
    
    // 抽象方法（子类必须实现）
    public abstract string Name { get; }
    public abstract int UIFormType { get; }
    
    // 动画控制
    public void SetAnimation(float progress);
}
```

### 5.4 UIFormExtension — 便捷扩展

```csharp
public static class UIFormExtension
{
    // 便捷方法：让 UIForm 实例可以直接调用组件功能
    public static T GetComponent<T>(this UIForm self) where T : BaseComponent;
    public static void OpenUIForm(this UIForm self, string uiFormName, object data);
    public static void CloseUIForm(this UIForm self);
}
```

**作用**：通过扩展方法，在 UIForm 实例上直接调用其他组件，减少代码嵌套。

### 5.5 完整链路总结

```
玩家点击 "开始游戏" 按钮
    │
    ▼
UIForm 按钮回调
    │
    ▼
UIFormExtension.OpenUIForm(this, "GameUIForm", null)
    │
    ▼
UIManager.LoadUIFormAsync("GameUIForm", callback)
    │
    ▼
ResourceManager.LoadAsset("UI/Game/GameUIForm")  →  加载 UI Prefab
    │
    ▼
UIForm.OnOpen()  →  初始化 UI 状态和动画
    │
    ▼
EventSystem.FireEvent(UIFormOpened)  →  通知其他模块
```

---

## 6. GameFramework 与 Unity UI 组件的链接

### 6.1 桥接机制

UGF 的 UI 系统通过以下机制与 Unity 的 UI 组件（UGUI）连接：

```
┌─────────────────────────────────────────────────────────────┐
│  Game Framework UI 层                                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  UIComponent                                            │  │
│  │    ├── UIManager (管理器)                                │  │
│  │    │     ├── LoadUIFormAsync()  → 加载 UI Prefab        │  │
│  │    │     ├── OpenUIForm()  → 打开 UI 表单                 │  │
│  │    │     └── CloseUIForm()  → 关闭 UI 表单                 │  │
│  │    └── UIHelper (可替换助手)                             │  │
│  └────────────────────────────────────────────────────────┘  │
│         │                                                       │
│         ▼                                                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  UIForm 实例 (继承自 UIForm)                             │  │
│  │    ├── 持有 UGUI GameObject                                │  │
│  │    ├── 访问 Unity Transform / Canvas / Button 等           │  │
│  │    └── 直接操作 Unity UI 组件                              │  │
│  └────────────────────────────────────────────────────────┘  │
│         │                                                       │
│         ▼                                                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Unity UGUI 组件                                         │  │
│  │    ├── Button (OnClick 回调)                              │  │
│  │    ├── Text / Image / Toggle / Slider 等                  │  │
│  │    └── Canvas (渲染容器)                                   │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 关键连接点

 连接点 | 说明 |
---------|------|
 **UI Prefab 加载** | UIManager 通过 ResourceManager 从 Addressables/Resource 目录加载 UI Prefab，实例化为 UIForm |
 **事件绑定** | UIForm 内部直接调用 `button.onClick.AddListener()` 绑定 Unity UI 事件 |
 **数据传递** | 通过 `UIFormOpenEventArgs` 在 OpenUIForm 时传递数据给新表单 |
 **层级管理** | UIManager 根据 UIFormType（0=窗口/1=对话框/2=覆盖层）管理 Canvas 层级 |

### 6.3 典型用法

```csharp
// 1. 打开 UI 表单
UI.OpenUIForm("MainMenu", new UIFormOpenEventArgs { /* 初始数据 */ });

// 2. UIForm 子类实现
public class MainMenuUIForm : UIForm
{
    // Unity UI 组件引用
    private Button startButton;
    private Button settingsButton;
    
    public override void OnOpen()
    {
        // 直接操作 Unity UI 组件
        startButton.onClick.AddListener(OnStartClicked);
        settingsButton.onClick.AddListener(OnSettingsClicked);
    }
    
    private void OnStartClicked()
    {
        UI.CloseUIForm(this.Name);
        UI.OpenUIForm("GamePlay", null);
    }
}

// 3. 通过 Event 系统解耦
EventSystem.Subscribe(GameEvents.LevelStarted, OnLevelStarted);
```

---

## 7. StarForce Demo 实例分析

### 7.1 项目结构

StarForce 是 UGF 的官方 Demo，展示了框架的实际应用：

```
StarForce/
├── Assets/
│   ├── Scripts/
│   │   ├── Launcher/        # 启动器场景（加载资源、初始化）
│   │   ├── Main/          # 主游戏场景（战斗、逻辑）
│   │   ├── Menu/          # 菜单场景（主菜单、设置）
│   │   └── Framework/     # 自定义组件扩展
├── Resources/
│   ├── UI/                  # UI Prefabs
│   ├── Entities/            # 实体 Prefabs
│   └── Configs/            # 配置数据表
```

### 7.2 Procedure 流程（流程管理）

StarForce 使用 Procedure 模块组织游戏流程：

```
LauncherProcedure  →  资源加载、初始化
    │
    ▼
MenuProcedure      →  主菜单、设置、百科
    │
    ▼
MainProcedure      →  游戏主循环（战斗、商店、事件）
    │
    ▼
EndProcedure       →  游戏结束、结算
```

```csharp
public abstract class BaseProcedure : Procedure
{
    public override void OnEnter() { /* 进入阶段 */ }
    public override void OnUpdate(float deltaTime) { /* 更新逻辑 */ }
    public override void OnLeave() { /* 离开阶段 */ }
}
```

### 7.3 数据驱动架构

StarForce 大量使用 DataTable 模块：

```csharp
// 加载配置表
DataTable table = GameEntry.DataTable.GetDataTable("GameData/Skills.xlsx");
// 或
DataTable table = GameEntry.DataTable.LoadDataTableAsync("GameData/Characters.xlsx");
```

### 7.4 Entity 系统

```csharp
// 创建实体
Entity player = GameEntry.Entity.CreateEntity("Player");
// 激活/停用实体
GameEntry.Entity.ActivateEntity("Player");
GameEntry.Entity.DeactivateEntity("Player");
// 销毁实体（放入对象池）
GameEntry.Entity.DestroyEntity("Player");
```

---

## 8. 开发最佳实践

### 8.1 组件注册

```csharp
// 在 GameFramework.prefab 中预设好组件
// 或动态添加
GameEntry.AddComponent(new CustomComponent());
```

### 8.2 UI 开发规范

```csharp
// 1. UIForm 继承
public class MyUIForm : UIForm { /* ... */ }

// 2. 使用 UIFormExtension 简化代码
ui.OpenUIForm("MyUIForm", data);

// 3. 通过 Event 解耦
EventSystem.FireEvent("UIOpened", uiForm);
```

### 8.3 资源管理

```csharp
// 加载资源
ResourceAssetHandle handle = GameEntry.Resource.LoadAssetHandleAsync("Prefabs/Player");
// 使用对象池
var player = GameEntry.ObjectPool.AcquireObject<Player>();
```

### 8.4 配置数据

```csharp
// 使用 Config 模块存储全局配置
GameEntry.Config["PlayerSpeed"] = 10.0f;
GameEntry.Config["Volume"] = 0.8f;
```

---

## 9. 常见问题

### Q1: GameEntry 和 MonoBehaviour 的关系是什么？

**A**: `GameFrameworkBehaviour`（MonoBehaviour 子类）挂载在 `GameFramework.prefab` 上。它桥接 Unity 的 `Awake/Start/Update` 到 `GameEntry` 的同名方法，让框架逻辑完全独立于 Unity 引擎。

### Q2: IUIForm 和 UIForm 的区别？

**A**: `IUIForm` 是接口，定义了 UI 表单的标准行为（打开、关闭、动画等）。`UIForm` 是抽象基类，实现了 `IUIForm` 接口，为所有 UI 表单提供通用功能。具体表单继承自 `UIForm` 并实现抽象属性。

### Q3: 如何扩展框架？

**A**: 
1. **新增组件**：继承 `GameFrameworkComponent`，添加到 `GameEntry`
2. **替换 Helper**：继承各模块的 Helper 类，注入到对应 Component
3. **扩展 UI**：创建自定义 UIForm 子类，注册到 UIManager

### Q4: Procedure 模块怎么用？

**A**: Procedure 管理游戏的阶段性流程。每个 Procedure 是游戏的一个阶段（启动→菜单→游戏→结束）。通过继承 `Procedure` 类，实现 `OnEnter/OnUpdate/OnLeave`，然后按顺序添加到 `ProcedureManager`。

### Q5: 对象池和引用池有什么区别？

**A**: 
- **ObjectPool**：用于频繁创建/销毁的游戏对象（如子弹、敌人），复用 GameObject 实例
- **ReferencePool**：用于管理资源引用计数，自动跟踪资源的使用情况，在引用数为 0 时自动释放资源

---

> 🐱 **总结**：UnityGameFramework 通过 **Component → Manager → Helper** 的三层架构，将 Unity 引擎和框架逻辑解耦。`GameEntry` 是总入口，`GameFrameworkBehaviour` 桥接 MonoBehaviour，`UIForm` 链路连接了框架与 UGUI。StarForce Demo 展示了这些模块在实战中的协同工作。

---

*文档基于 UnityGameFramework (GitHub: EllanJiang/UnityGameFramework, ⭐2.5k) 和 StarForce Demo (⭐966) 整理。*
    Title = GameEntry.Localization.GetString("AskQuitGame.Title"),
    Message = GameEntry.Localization.GetString("AskQuitGame.Message"),
    OnClickConfirm = delegate (object userData) { /* 回调 */ },
});
```

**工作流程**：
1. `UIExtension.OpenUIForm()` 通过 `DRUIForm` 数据表查找 `AssetName`
2. 通过 `AssetUtility.GetUIFormAsset()` 转换资产名
3. `UIManager.OpenUIForm()` 加载 UI Prefab
4. 实例化 `UIForm` 并调用 `OnOpen()`

---

### 10.2 登录功能示例 — Procedure 流程管理

StarForce 的启动流程是典型的登录/启动流程：

```csharp
// ProcedureLaunch → 启动器（检查更新）
// ProcedureCheckVersion → 检查版本
// ProcedureInitResources → 初始化资源
// ProcedureMenu → 主菜单（含登录入口）
// ProcedureMain → 主游戏

// ProcedureBase 的 OnEnter 方法
protected override void OnEnter(ProcedureOwner procedureOwner)
{
    // 1. 订阅事件
    GameEntry.Event.Subscribe(OpenUIFormSuccessEventArgs.EventId, OnOpenUIFormSuccess);
    // 2. 打开 UI
    GameEntry.UI.OpenUIForm(UIFormId.MenuForm, this);
}

// 3. UI 打开成功后回调
private void OnOpenUIFormSuccess(object sender, GameEventArgs e)
{
    OpenUIFormSuccessEventArgs ne = (OpenUIFormSuccessEventArgs)e;
    m_MenuForm = (MenuForm)ne.UIForm.Logic;
}
```

---

### 10.3 Entity 与 ObjectPool 示例 — HPBar

StarForce 的 `HPBarComponent` 展示了 Entity + ObjectPool 的配合：

```csharp
// 1. 创建对象池
m_HPBarItemObjectPool = GameEntry.ObjectPool.CreateSingleSpawnObjectPool<HPBarItemObject>("HPBarItem", 16);

// 2. 显示 HP 血条
public void ShowHPBar(Entity entity, float fromHPRatio, float toHPRatio)
{
    HPBarItem hpBarItem = GetActiveHPBarItem(entity);
    if (hpBarItem == null)
    {
        hpBarItem = CreateHPBarItem(entity);
        m_ActiveHPBarItems.Add(hpBarItem);
    }
    hpBarItem.Init(entity, m_CachedCanvas, fromHPRatio, toHPRatio);
}

// 3. 从对象池获取或创建实例
private HPBarItem CreateHPBarItem(Entity entity)
{
    HPBarItemObject hpBarItemObject = m_HPBarItemObjectPool.Spawn();
    if (hpBarItemObject != null)
    {
        hpBarItem = (HPBarItem)hpBarItemObject.Target;
    }
    else
    {
        hpBarItem = Instantiate(m_HPBarItemTemplate);
        Transform transform = hpBarItem.GetComponent<Transform>();
        transform.SetParent(m_HPBarInstanceRoot);
        transform.localScale = Vector3.one;
        m_HPBarItemObjectPool.Register(HPBarItemObject.Create(hpBarItem), true);
    }
    return hpBarItem;
}
```

---

### 10.4 设置界面示例 — SettingForm

```csharp
public class SettingForm : UGuiForm
{
    // UGUI 组件引用
    [SerializeField] private Toggle m_MusicMuteToggle = null;
    [SerializeField] private Slider m_MusicVolumeSlider = null;
    [SerializeField] private Toggle m_SoundMuteToggle = null;

    public void OnMusicMuteChanged(bool isOn)
    {
        GameEntry.Sound.Mute("Music", !isOn);
        m_MusicVolumeSlider.gameObject.SetActive(isOn);
    }

    public void OnSubmitButtonClick()
    {
        GameEntry.Setting.SetString(Constant.Setting.Language, m_SelectedLanguage.ToString());
        GameEntry.Setting.Save();
        GameEntry.Sound.StopMusic();
        GameEntry.Shutdown(ShutdownType.Restart);
    }

    // OnOpen: 从 SoundComponent 和 LocalizationComponent 同步状态
    protected override void OnOpen(object userData)
    {
        base.OnOpen(userData);
        m_MusicMuteToggle.isOn = !GameEntry.Sound.IsMuted("Music");
        m_MusicVolumeSlider.value = GameEntry.Sound.GetVolume("Music");
        // ...
    }
}
```

---

### 10.5 DataTable 数据驱动示例

StarForce 使用 `DRUIForm` 数据表配置 UI 表单信息：

```csharp
// 通过 UIExtension 从 DataTable 获取 UI 配置
IDataTable<DRUIForm> dtUIForm = GameEntry.DataTable.GetDataTable<DRUIForm>();
DRUIForm drUIForm = dtUIForm.GetDataRow(uiFormId);

// 使用数据表的配置
string assetName = AssetUtility.GetUIFormAsset(drUIForm.AssetName);
int? handleId = uiComponent.OpenUIForm(
    assetName,
    drUIForm.UIGroupName,
    Constant.AssetPriority.UIFormAsset,
    drUIForm.PauseCoveredUIForm,
    userData
);
```

---

### 10.6 完整使用示例汇总

 关键接口/类 | 使用方式 |
-------------|----------|
 `UIComponent.OpenUIForm()` | 通过 UIFormId 打开 UI |
 `Procedure.OnEnter()` | 初始化 UI 并订阅事件 |
 `GameEntry.Entity.CreateEntity()` | 创建、激活、销毁实体 |
 `ObjectPool.Spawn()/Unspawn()` | 复用对象，减少 GC |
 `DataTable.GetDataTable<T>()` | 加载配置数据 |
 `GameEntry.Sound.Mute()/SetVolume()` | 控制音乐/音效 |
 `GameEntry.Localization.GetString()` | 获取多语言文本 |
 `GameEntry.Setting.SetString()/Save()` | 持久化设置 |