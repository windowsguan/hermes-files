# UnityGameFramework 完整指南

> 基于官方仓库 [EllanJiang/UnityGameFramework](https://github.com/EllanJiang/UnityGameFramework) 源码整理
> 核心结论：**`GameFrameworkBehaviour` 在官方源码中不存在**——实际桥梁是 `GameFrameworkComponent`

---

## 1. 架构总览

```
┌─────────────────────────────────────────────────────┐
│                  Unity 层 (MonoBehaviour)              │
│  GameFramework.prefab (20+ GameObject + Component)    │
├─────────────────────────────────────────────────────┤
│              GameEntry (静态入口)                      │
│  注册组件 → 分发生命周期 (Awake/Start/Update)           │
├─────────────────────────────────────────────────────┤
│        GameFramework Core (核心库层)                    │
│  IGameFramework → I*Manager → *Component               │
└─────────────────────────────────────────────────────┘
```

### 关键澄清：`GameFrameworkBehaviour` 已不存在

旧版文档中提到的 `GameFrameworkBehaviour` 是一个**过时的概念**。当前官方源码中：
- 实际桥梁类为 **`GameFrameworkComponent : MonoBehaviour`**
- 每个具体组件（如 `ResourceComponent`、`UIComponent`）均继承自 `GameFrameworkComponent`
- `GameFrameworkComponent` 在 `Awake()` 中自动调用 `GameEntry.RegisterComponent(this)` 完成注册

---

## 2. 核心入口：`GameEntry`

**文件**: `Scripts/Runtime/Base/GameEntry.cs`

`GameEntry` 是 Unity 层与 GameFramework Core 层的**核心桥梁**：

```csharp
public static class GameEntry
{
    // 组件注册（GameFrameworkComponent.Awake() 中调用）
    internal static void RegisterComponent(GameFrameworkComponent gameFrameworkComponent);

    // 获取组件（3 种重载）
    public static T GetComponent<T>() where T : GameFrameworkComponent;
    public static GameFrameworkComponent GetComponent(Type type);
    public static GameFrameworkComponent GetComponent(string typeName);

    // 关闭框架
    public static void Shutdown(ShutdownType shutdownType);
}
```

### ShutdownType 枚举

```csharp
public enum ShutdownType
{
    None,       // 仅关闭组件，不退出
    Restart,    // 重新加载 GameFrameworkSceneId = 0 场景
    Quit,        // 退出应用 (Application.Quit())
    ProcessExit  // 进程退出
}
```

### GameFrameworkComponent 基类

```csharp
public abstract class GameFrameworkComponent : MonoBehaviour
{
    protected virtual void Awake()
    {
        GameEntry.RegisterComponent(this);
    }
}
```

所有具体组件（`ResourceComponent`、`UIComponent` 等）继承此基类，在 `Awake()` 时自动注册到 `GameEntry` 的组件链表中。

---

## 3. Base 模块

| 文件 | 作用 |
|------|------|
| `BaseComponent.cs` | 基础组件：管理帧率、游戏速度、后台运行、DPI 等全局设置 |
| `GameEntry.cs` | 静态入口：组件注册、获取、关闭框架 |
| `GameFrameworkComponent.cs` | 抽象基类，所有组件的父类，继承 `MonoBehaviour` |
| `ShutdownType.cs` | 关闭类型枚举 |

### BaseComponent 主要属性

```csharp
public sealed class BaseComponent : GameFrameworkComponent
{
    // 编辑器资源模式（EditorResourceMode, EditorLanguage, EditorResourceHelper）
    // 渲染设置（FrameRate, GameSpeed, RunInBackground, NeverSleep）
    // 辅助器（TextHelper, VersionHelper, LogHelper, CompressionHelper, JsonHelper）
    // 状态查询（IsGamePaused, IsNormalGameSpeed）
}
```

---

## 4. UI 系统（重点模块）

### 4.1 组件架构

```
UIComponent (Component 层)
    │
    ├── IUIManager (Core 层管理器)
    │     ├── 管理 UIGroup（界面组）
    │     ├── 管理 UIForm 实例
    │     └── 事件分发
    │
    ├── UIForm (Runtime 层，继承 MonoBehaviour)
    │     ├── 属性：SerialId, UIFormAssetName, UIGroup, DepthInUIGroup
    │     ├── 方法：OnInit(), OnRecycle(), OnOpen(), OnClose()
    │     └── Handle (返回 gameObject)
    │
    └── UIFormLogic (Runtime 层，继承 MonoBehaviour)
            ├── OnInit(userData), OnRecycle(), OnOpen(userData), OnClose()
            ├── Available, Visible 状态管理
            └── 开发者可继承并实现自定义逻辑
```

### 4.2 UIComponent 接口

**文件**: `Scripts/Runtime/UI/UIComponent.cs`

```csharp
public sealed partial class UIComponent : GameFrameworkComponent
{
    // --- UIGroup 管理 ---
    public int UIGroupCount;
    public bool CreateUIGroup(string name);
    public bool DeleteUIGroup(string name);
    public bool IsUIGroupExist(string name);
    public void SetUIGroupDepth(string name, int depth);
    public void SetUIGroupSortMode(string name, UIGroupSortMode mode);
    public void SetUIGroupHelper(string name, string typeName);

    // --- UIForm 操作 ---
    public void OpenUIForm(int uiGroupIndex, string name, float pausing, object userData);
    public void OpenUIForm(string uiGroupName, string name, float pausing, object userData);
    public void CloseUIForm(int serialId, object userData);
    public void ResetUIForm();
    public IUIForm GetUIForm(int serialId);
    public void SortUIFormsInUIGroup(string name);

    // --- 对象池设置 ---
    public float InstanceAutoReleaseInterval;
    public int InstanceCapacity;
    public float InstanceExpireTime;
    public int InstancePriority;
}
```

### 4.3 UIForm 接口

**文件**: `Scripts/Runtime/UI/UIForm.cs`

```csharp
public sealed class UIForm : MonoBehaviour, IUIForm
{
    public int SerialId { get; }
    public string UIFormAssetName { get; }
    public object Handle { get; }        // 返回 gameObject
    public IUIGroup UIGroup { get; }
    public int DepthInUIGroup { get; }
    public bool PauseCoveredUIForm { get; }
    public UIFormLogic Logic { get; }

    public void OnInit(int serialId, string uiFormAssetName, IUIGroup uiGroup,
                       bool pauseCoveredUIForm, bool isNewInstance, object userData);
    public void OnRecycle();
    public void OnOpen(object userData);
    public void OnClose();
    public void OnUpdate(float elapseTime, float realDeltaTime);
    public void OnPause();
    public void OnResume();
}
```

### 4.4 UIFormLogic 抽象基类

**文件**: `Scripts/Runtime/UI/UIFormLogic.cs`

```csharp
public abstract class UIFormLogic : MonoBehaviour
{
    public UIForm UIForm { get; }
    public string Name { get; set; }
    public bool Available { get; }
    public bool Visible { get; set; }
    public Transform CachedTransform { get; }

    // 虚方法（开发者覆盖）
    protected internal virtual void OnInit(object userData);
    protected internal virtual void OnRecycle();
    protected internal virtual void OnOpen(object userData);
    protected internal virtual void OnClose();
    protected internal virtual void OnUpdate(float elapseTime, float realDeltaTime);
    protected internal virtual void OnPause();
    protected internal virtual void OnResume();
}
```

### 4.5 UI 辅助类

| 文件 | 作用 |
|------|------|
| `DefaultUIFormHelper.cs` | UIForm 默认辅助器（加载、缓存管理） |
| `DefaultUIGroupHelper.cs` | UIGroup 默认辅助器 |
| `UIFormHelperBase.cs` | UIForm 辅助器基类 |
| `UIGroupHelperBase.cs` | UIGroup 辅助器基类 |
| `UIFormLogic.cs` | UI 逻辑基类 |
| `UIIntKey.cs` | 整型 UI 键值 |
| `UIStringKey.cs` | 字符串 UI 键值 |
| 事件参数类 | `OpenUIFormSuccessEventArgs`, `OpenUIFormFailureEventArgs` 等 |

### 4.6 UI 系统与 Unity UI 组件的关联

```
UIForm (MonoBehaviour)
    ├── 挂载在 Unity GameObject 上
    ├── 通过 Handle 属性返回 gameObject
    ├── UIFormLogic 挂载在同一 GameObject 上
    └── UI 组件通过 Resource 系统加载 UI Prefab，实例化为 UIForm

使用流程：
1. 设计 UI Prefab（包含 Canvas, Panel, Button 等 Unity UI 组件）
2. 在 Prefab 的根 GameObject 挂载 UIForm + 自定义 UIFormLogic 子类
3. UIComponent.OpenUIForm() → 从资源加载 UI Prefab
4. UIForm.OnInit() → 初始化 UIFormLogic
5. 交互通过 UIFormLogic 中的 Unity UI 组件（Button, InputField 等）
```

---

## 5. Event 模块

### EventComponent 接口

**文件**: `Scripts/Runtime/Event/EventComponent.cs`

```csharp
public sealed class EventComponent : GameFrameworkComponent
{
    public int EventHandlerCount { get; }
    public int EventCount { get; }

    public int Count(int id);
    public bool Check(int id, EventHandler<GameEventArgs> handler);
    public void Subscribe(int id, EventHandler<GameEventArgs> handler);
    public void Unsubscribe(int id, EventHandler<GameEventArgs> handler);
    public void SetDefaultHandler(EventHandler<GameEventArgs> handler);
    public void RemoveDefaultHandler();
    public void Fire(int id, GameEventArgs eventArgs);
    public void Fire(int id);
}
```

---

## 6. Resource 模块

**文件**: `Scripts/Runtime/Resource/ResourceComponent.cs`

```csharp
public sealed class ResourceComponent : GameFrameworkComponent
{
    // 加载资源（多种重载）
    public AssetHandle LoadAsset(string assetPath, float cacheTime, int priority, object userData);
    public AssetHandle LoadAsset(string assetPath, object userData);
    public AssetHandle LoadInstantAsset(string assetPath);
    public void SubAssetDependencies(string assetPath, List<string> dependAssetPaths);

    // 保存/加载游戏
    public void SaveGame(Action<bool> completeCallback, object userData);
    public void LoadGame(Action<bool> completeCallback, object userData);

    // 资源更新
    public bool IsUpdateResourceAvailable { get; }
    public void UpdateResourceAsync(...);

    // 资源验证
    public void VerifyResourceAsync(...);

    // 资源应用
    public void ApplyUpdateAsync(...);

    // 子资产
    public void ClearSubAssetDependencies();
    public void ClearCachedAssets();

    // 编辑器资源辅助器
    public IResourceManager EditorResourceHelper { get; set; }
}
```

---

## 7. Scene 模块

**文件**: `Scripts/Runtime/Scene/SceneComponent.cs`

```csharp
public sealed class SceneComponent : GameFrameworkComponent
{
    public int ActiveSceneBuildIndex { get; }
    public string ActiveSceneName { get; }
    public Scene ActiveScene { get; }

    public void LoadScene(string sceneName, float cacheTime, int priority, object userData);
    public void LoadScene(int sceneBuildIndex, ...);
    public void LoadSceneAsync(string sceneName, SceneLoadMode loadMode, ...);
    public void UnloadScene(string sceneName, object userData);
    public void UnloadSceneAsync(string sceneName, ...);
    public void DisposeScene(string sceneName);
    public bool IsSceneLoaded(string sceneName);
}
```

---

## 8. Entity 模块

**文件**: `Scripts/Runtime/Entity/EntityComponent.cs`

```csharp
public sealed partial class EntityComponent : GameFrameworkComponent
{
    // EntityGroup 管理
    public int EntityGroupCount { get; }
    public bool CreateEntityGroup(string name);
    public bool DeleteEntityGroup(string name);
    public bool IsEntityGroupExist(string name);
    public void SetEntityGroupDepth(string name, int depth);

    // Entity 操作
    public Entity ShowEntity(string entityGroupName, string name, object userData);
    public Entity ShowEntity(int entityGroupIndex, string name, ...);
    public void HideEntity(int serialId, object userData);
    public void HideEntity(Entity entity, object userData);
    public Entity GetEntity(int serialId);
    public void ResetEntity();
}
```

### Entity 和 EntityLogic

```csharp
public sealed class Entity : MonoBehaviour, IEntity
{
    public int SerialId { get; }
    public string EntityAssetName { get; }
    public object Handle { get; }
    public EntityLogic Logic { get; }
    public void OnInit(...);
    public void OnRecycle();
    public void OnShow(object userData);
    public void OnHide(object userData);
}

public abstract class EntityLogic : MonoBehaviour
{
    protected internal virtual void OnInit(object userData);
    protected internal virtual void OnRecycle();
    protected internal virtual void OnShow(object userData);
    protected internal virtual void OnHide(object userData);
    protected internal virtual void OnUpdate(float elapseTime, float realDeltaTime);
}
```

---

## 9. FSM 模块

**文件**: `Scripts/Runtime/Fsm` 目录（非 Core 子目录，直接在 Fsm/ 下）

```csharp
public sealed class FsmComponent : GameFrameworkComponent
{
    public void AddFsm<T>(string name, IFsmSetTransitions<T> transitions);
    public IFsm<T> GetFsm<T>(string name);
    public void ChangeFsmState<T>(string name, string stateName);
    public void RemoveFsm<T>(string name);
}
```

---

## 10. Procedure（流程）模块

```csharp
public sealed class ProcedureComponent : GameFrameworkComponent
{
    public void AddProcedure(string name);
    public void RemoveProcedure(string name);
    public ProcedureBase GetProcedure(string name);
}
```

---

## 11. ObjectPool 模块

```csharp
public sealed class ObjectPoolComponent : GameFrameworkComponent
{
    public T BorrowInstance<T>(...);
    public void ReturnInstance<T>(T reference);
    public void ReleaseUnusedInstances();
}
```

---

## 12. 完整模块清单

| 模块 | 核心类 | 功能概述 |
|------|---------|----------|
| Base | `BaseComponent`, `GameEntry`, `GameFrameworkComponent` | 框架基础、入口、组件基类 |
| UI | `UIComponent`, `UIForm`, `UIFormLogic` | 界面管理、UIForm 生命周期 |
| Event | `EventComponent` | 事件订阅/发布系统 |
| Resource | `ResourceComponent` | 资源加载、更新、保存/加载 |
| Scene | `SceneComponent` | 场景加载/卸载 |
| Entity | `EntityComponent`, `Entity`, `EntityLogic` | 实体管理 |
| Fsm | `FsmComponent` | 有限状态机 |
| Procedure | `ProcedureComponent` | 流程控制 |
| ObjectPool | `ObjectPoolComponent` | 对象池 |
| Config | `ConfigComponent` | 配置表管理 |
| DataNode | `DataNodeComponent` | 数据节点 |
| DataTable | `DataTableComponent` | 数据表管理 |
| Debugger | `DebuggerComponent` | 调试面板、日志、性能监控 |
| Download | `DownloadComponent` | 文件下载 |
| FileSystem | `FileSystemComponent` | 文件系统操作 |
| Localization | `LocalizationComponent` | 本地化/多语言 |
| Network | `NetworkComponent` | 网络连接管理 |
| ReferencePool | `ReferencePoolComponent` | 引用池 |
| Setting | `SettingComponent` | 设置管理 |
| Sound | `SoundComponent` | 音频管理 |
| Variable | `VariableComponent` | 变量管理 |
| WebRequest | `WebRequestComponent` | HTTP 请求 |

---

## 13. 各模块 Core 层接口

### 公共接口层次

```
IGameFramework
    ├── IBaseFramework → BaseComponent
    ├── IUIManager → UIComponent
    ├── IEventManager → EventComponent
    ├── IResourceManager → ResourceComponent
    ├── ISceneManager → SceneComponent
    ├── IEntityManager → EntityComponent
    ├── IFsmManager → FsmComponent
    ├── IProcedureManager → ProcedureComponent
    ├── IObjectPoolManager → ObjectPoolComponent
    ├── IConfigManager → ConfigComponent
    ├── IDebuggerManager → DebuggerComponent
    ├── IDownloadManager → DownloadComponent
    ├── IFileSystemManager → FileSystemComponent
    ├── ILocalizationManager → LocalizationComponent
    ├── INetworkManager → NetworkComponent
    ├── IReferencePoolManager → ReferencePoolComponent
    ├── ISettingManager → SettingComponent
    ├── ISoundManager → SoundComponent
    ├── IVariableManager → VariableComponent
    └── IWebRequestManager → WebRequestComponent
```

---

## 14. 生命周期与调用链

```
Unity 引擎                    GameFramework
    │                               │
    ▼                               ▼
MonoBehaviour.Awake() → GameFrameworkComponent.Awake()
    │                               │
    │                               ▼
    │                          GameEntry.RegisterComponent(this)
    │                               │
    ▼                               ▼
MonoBehaviour.Start() → Component.Start() → 初始化 Manager + Helper
    │                               │
    ▼                               ▼
MonoBehaviour.Update() → Component.Update() → Manager.Update()
    │                               │
    ▼                               ▼
MonoBehaviour.OnDestroy() → GameEntry.Shutdown(ShutdownType)
```

---

## 15. 开发者使用示例

### 15.1 打开 UI 界面

```csharp
// 获取 UIComponent
UIComponent ui = GameEntry.GetComponent<UIComponent>();

// 打开界面（通过 UIFormLogic 子类处理）
ui.OpenUIForm("MainUI", "MainMenu", 0f, null);

// 在自定义 UIFormLogic 中：
public class MainMenuUIFormLogic : UIFormLogic
{
    protected internal override void OnInit(object userData)
    {
        // 绑定 Unity UI 组件
        Button startBtn = gameObject.GetComponentInChildren<Button>();
        startBtn.onClick.AddListener(OnStartGame);
    }

    protected internal override void OnOpen(object userData)
    {
        Visible = true;
        // 界面打开逻辑
    }

    private void OnStartGame()
    {
        // 游戏开始逻辑
    }
}
```

### 15.2 加载资源

```csharp
ResourceComponent resource = GameEntry.GetComponent<ResourceComponent>();
AssetHandle handle = resource.LoadAsset("Assets/UI/MainMenu", null);
```

### 15.3 事件系统

```csharp
EventComponent eventComp = GameEntry.GetComponent<EventComponent>();
eventComp.Subscribe(1, OnGameStartEvent);

private void OnGameStartEvent(object sender, GameEventArgs e)
{
    // 处理事件
}
```

---

## 16. 重要说明

1. **`GameFrameworkBehaviour` 已不存在**：旧文档中的 `GameFrameworkBehaviour` 是过时的命名。实际框架使用 `GameFrameworkComponent : MonoBehaviour` 作为桥梁，所有具体组件继承此基类。
2. **UIForm ↔ Unity UI 的关系**：`UIForm` 继承 `MonoBehaviour`，挂载在 UI Prefab 根节点上，通过 `Handle` 属性返回 `gameObject`。开发者在 `UIFormLogic` 中直接操作 Unity UI 组件（Button、InputField、Text 等）。
3. **GameFramework.prefab 结构**：包含 20+ GameObject，每个对应一个组件（FSM, Resource, UI, Event, Entity 等），每个 GameObject 挂载对应的 *Component。
4. **GameEntry 是统一入口**：所有组件通过 `GameEntry.GetComponent<T>()` 获取，通过 `GameEntry.Shutdown()` 关闭框架。

---

*文档基于 EllanJiang/UnityGameFramework 官方仓库源码整理*
*仓库地址：https://github.com/EllanJiang/UnityGameFramework*