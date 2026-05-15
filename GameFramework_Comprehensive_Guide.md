# GameFramework 综合学习指南

> 整合来源：drflower.top 博客系列 + 官方仓库源码 + DeepWiki + TowerDefense Demo + gf学习笔记

---

## 一、学习笔记核心要点

### 1.1 事件系统

```csharp
// 订阅事件 — 事件触发时回调
GF.Event.Subscribe(LoadConfigSuccessEventArgs.EventId, OnLoadConfigSuccess);

// 触发事件 — Fire 触发事件并调用 Create
GF.Event.Fire(this, PlayerDataChangedEventArgs.Create(tp, oldValue, value));
```

**事件链路**（从 Manager → Component → Procedure）：

```
IDataProvider<T>.ReadDataSuccess 事件
    → DataProvider.ReadData() → Fire ReadDataSuccessEventArgs
    → ConfigManager.ReadData()
    → ConfigComponent.OnReadDataSuccess → Fire LoadConfigSuccessEventArgs
    → ProcedurePreload 订阅了此事件
```

### 1.2 组件注册机制

```csharp
// GameEntry.RegisterComponent() 注册所有继承 GameFrameworkComponent 的类
// 搜索 ": GameFrameworkComponent" 就能找到框架所有组件
```

所有 `*Component` 都继承 `GameFrameworkComponent : MonoBehaviour`，在 `Awake()` 中自动注册。

### 1.3 流程系统 (Procedure)

**完整启动流程链**：

```
ProcedureLaunch
    → ProcedureSplash
        → ProcedureInitResource (本地 AB 包)
        → ProcedureCheckVersion (网络：检查版本号)
            → m_NeedUpdateVersion==1 → ProcedureUpdateVersion
            → m_NeedUpdateVersion==0 → ProcedureCheckResources
                → m_NeedUpdateResources → ProcedureUpdateResources → ProcedurePreload
                → 无需加载 → ProcedurePreload
    → ProcedurePreload
        → ProcedureLoadingScene
```

**Procedure 关键代码**：

```csharp
using ProcedureOwner = GameFramework.Fsm.IFsm<GameFramework.Procedure.IProcedureManager>;
// ProcedureOwner 是 FSM 中管理 ProcedureManager 的状态机

// 网络请求事件订阅
GameEntry.Event.Subscribe(WebRequestSuccessEventArgs.EventId, OnWebRequestSuccess);
GameEntry.Event.Subscribe(WebRequestFailureEventArgs.EventId, OnWebRequestFailure);

// 版本检查 URL 构建
GameEntry.WebRequest.AddWebRequest(
    Utility.Text.Format(GameEntry.BuiltinData.BuildInfo.CheckVersionUrl, GetPlatformPath()),
    this
);
```

**ProcedurePreload 预加载**：

```csharp
protected override void OnEnter(ProcedureOwner procedureOwner)
{
    base.OnEnter(procedureOwner);
    GameEntry.Event.Subscribe(LoadConfigSuccessEventArgs.EventId, OnLoadConfigSuccess);
    GameEntry.Event.Subscribe(LoadConfigFailureEventArgs.EventId, OnLoadConfigFailure);
    GameEntry.Event.Subscribe(LoadDictionarySuccessEventArgs.EventId, OnLoadDictionarySuccess);
    GameEntry.Event.Subscribe(LoadDictionaryFailureEventArgs.EventId, OnLoadDictionaryFailure);

    PreloadResources();  // LoadConfig, LoadDictionary, PreLoadAllData
}

private void PreloadResources()
{
    LoadConfig("DefaultConfig");
    LoadDictionary("Default");
    GameEntry.Data.PreLoadAllData();
}
```

---

## 二、drflower.top 博客系列 — 10 篇 GameFramework 解析

### 文章索引

| # | 标题 | 日期 | 核心内容 |
|---|------|------|----------|
| 1 | GameFramework 解析：开篇 | 2021-10-23 | 框架概述，19 个内置模块简介 |
| 2 | GameFramework 解析：塔防 Demo | 2021-10-23 | TowerDefense Demo 介绍：5 个关卡、5 种塔、敌人类型 |
| 3 | GameFramework 解析：整体架构 | 2021-10-24 | 三层架构：GF 层 → UGF 层 → Game 层 |
| 4 | GameFramework 解析：有限状态机（FSM） | 2021-11-02 | FsmState / FsmBase / IFsm / FsmManager |
| 5 | GameFramework 解析：流程（Procedure） | 2021-11-09 | Procedure 是对 FSM 的封装，用于游戏生命周期管理 |
| 6 | GameFramework 解析：编写游戏启动流程 | 2021-11-10 | 热更新启动流程设计 |
| 7 | GameFramework 解析：界面（UI） | 2021-11-17 | UIGroup + UIForm，UI 栈和生命周期管理 |
| 8 | GameFramework 解析：引用池（ReferencePool） | 2021-11-23 | 防止 C# 对象频繁 GC，实现 IReference |
| 9 | GameFramework 解析：对象池（ObjectPool） | 2021-11-30 | GameObject 对象池，ObjectBase / ObjectPool |
| 10 | GameFramework 解析：声音（Sound） | 2021-12-07 | SoundAgent / SoundComponent，统一音量管理和优先级调度 |

### 2.1 整体架构（三层模型）

```
┌──────────────────────────────────────────────────────┐
│  Game 层（游戏逻辑层）                                   │
│  - 只与 UGF 层接触                                        │
│  - 通过接口调用各 Manager                                   │
├──────────────────────────────────────────────────────┤
│  UGF 层（Unity Game Framework 层）                        │
│  - 实现依赖 Unity 的逻辑                                       │
│  - 实例化并初始化各模块（*Component : MonoBehaviour）        │
│  - 提供可视化配置（Inspector）                                 │
├──────────────────────────────────────────────────────┤
│  GF 层（GameFramework Core 层）                             │
│  - 各模块的具体实现，不依赖引擎                                    │
│  - 若需引擎参数，通过 UGF 层 Component 传入                     │
└──────────────────────────────────────────────────────┘
```

### 2.2 有限状态机（FSM）

```
FsmState
    ├── OnEnter(): 进入状态时调用
    ├── OnLeave(): 离开状态时调用
    ├── OnUpdate(): 每帧调用
    └── ChangeState(): 切换状态

FsmBase / IFsm
    ├── 状态机核心
    └── 管理状态集合和当前状态

IFsmManager / FsmManager
    └── 状态机管理器，创建/销毁状态机
```

**使用场景**：玩家控制、怪物 AI、UI 状态、游戏流程控制。

### 2.3 流程（Procedure）

```
Procedure 是对 FSM 的封装：
    ProcedureBase
        ├── OnEnter(): 进入流程
        ├── OnLeave(): 离开流程
        ├── OnUpdate(): 每帧更新
        └── 通过 ChangeState 切换流程

IFsmManager / IFsm<GameFramework.Procedure.IProcedureManager>
```

**典型流程链**：
```
Launch → Splash → InitResource → CheckVersion → UpdateVersion
  → CheckResources → UpdateResources → Preload → LoadingScene → ...
```

### 2.4 UI 系统

```
UIManager
    ├── UIGroup (界面组)
    │   ├── 链表管理 UI 层级
    │   ├── 支持将任意界面激活到最上层
    │   └── 同一组永远只有一个 UIForm 处于最上层
    │
    └── UIForm (界面)
        ├── OnInit / OnOpen / OnClose / OnPause / OnResume
        ├── 被覆盖的界面会收到 Cover/Reveal 事件
        └── UIFormLogic 基类定义了标准生命周期
```

### 2.5 引用池（ReferencePool）

```
ReferencePool
    ├── ReferenceCollection: 管理引用集合
    ├── ReferencePoolInfo: 统计信息
    └── IReference 接口
        └── Clear(): 恢复初始状态
```

**用途**：防止普通 C# 对象被频繁创建销毁，减少 GC 压力。

### 2.6 对象池（ObjectPool）

```
ObjectBase
    ├── m_Target: 引用真正的目标对象
    │
    ├── Object / ObjectInfo: 对象信息
    │
    ├── ObjectPoolBase / IObjectPool / ObjectPool
    │   └── ReleaseObjectFilterCallback
    │
    └── IObjectPoolManager / ObjectPoolManager
```

**与引用池的区别**：对象池专门管理 `UnityEngine.Object` 派生对象（如 GameObject）。

### 2.7 声音系统

```
SoundAgent
    ├── 替代手动创建 AudioSource
    ├── 按类型分类管理
    ├── 限制最大并发播放数
    └── 支持优先级调度
```

---

## 三、TowerDefense-GameFramework-Demo 分析

### 3.1 项目概述

- **原型**：Unity 官方 Tower Defense Template (1.4)
- **引擎**：Unity 2019.4.1f1
- **框架**：GameFramework 2020.12.31
- **用途**：个人对 GF 的学习实践，也是他人的学习参考

### 3.2 游戏设计

**5 个关卡**，每个关卡的地形、敌人、可用塔均不同：
1. **5 种塔**：加农炮塔、火箭炮塔、激光炮塔、能量塔、电子脉冲塔
2. **敌人类型**：虫子、直升机、坦克、Boss 及其"超级"版本
3. **能量系统**：初始能量 + 击杀获取 + 能量塔产出
4. **基地**：敌人攻击目标，血量为 0 即失败

### 3.3 使用的 GF 模块

项目使用了 GF 的多个模块：
- **全局配置**（Config）：数据配置（Excel → 二进制）
- **数据表**（DataTable）：运行时数据加载
- **实体**（Entity）：游戏对象管理
- **事件**（Event）：模块间通信
- **文件系统**（FileSystem）：文件操作
- **有限状态机**（FSM）：流程控制
- **本地化**（Localization）：多语言支持
- **对象池**（ObjectPool）：GameObject 复用
- **引用池**（ReferencePool）：C# 对象缓存
- **流程**（Procedure）：游戏启动流程
- **资源**（Resource）：资源加载/热更
- **场景**（Scene）：场景管理
- **声音**（Sound）：音频管理
- **UI**：界面管理
- **网络**（Network）：版本检查、资源更新

### 3.4 关键实现

| 功能 | 实现方式 |
|------|----------|
| 数据配置 | Excel → 二进制文件，运行时加载 |
| 本地化 | Localization + 资源变体 |
| 引用池 | 大量重复使用的 C# 对象使用引用池缓存 |
| 资源打包 | 正确配置分包信息，0 冗余、0 循环引用 |
| 热更新 | 启动检测版本 + 基本资源更新 |
| 分包下载 | 每个关卡资源独立分包，按需下载 |

### 3.5 注意事项

- Editor 模式下默认读取工程内资源，不读 AB 包、不更新
- 测试更新模式：Base 组件取消 Editor Resource Mode，Resource 组件设为 Updatable 模式
- 打包资源后可用 HFS 等工具本地部署测试

---

## 四、DeepWiki 深度分析

### 4.1 UnityGameFramework Wiki 要点

**核心架构总结**：

```
三层组件模式（每个系统都遵循）：
    Unity 层: XxxComponent : GameFrameworkComponent : MonoBehaviour
    管理器层: IXxxManager 接口 + XxxManager 实现
    辅助层:   XxxHelperBase → 提供定制点
```

**GameEntry 作为中心访问点**：
- `GetComponent<T>()` 获取任意组件
- `Shutdown()` 关闭框架
- 维护组件链表，所有组件在 `Awake()` 时注册

### 4.2 StarForce Wiki 要点

**StarForce** 是一个太空射击游戏 Demo，展示 GF 的实际应用：

**5 个核心架构方法**：
1. **Component-Based Design**：围绕离散组件构建，由 GameEntry 统一管理
2. **Procedure-Based Game Flow**：用 Procedure 系统管理生命周期
3. **Data-Driven Configuration**：数据与逻辑分离，外部文件加载
4. **Entity System**：清晰的实体继承层次
5. **Resource Management**：完整资源加载、更新、管理

**数据驱动架构流程**：
```
DataTableGenerator → DataTableProcessor → .bytes files + DR*.cs classes
运行时：DataTableComponent → LoadDataTable() → DR* Objects → Game Entities
```

**项目结构**：
1. Launcher Scene：GF 初始化入口
2. Main Scene：主要游戏元素
3. Menu Scene：菜单 UI

---

## 五、综合对比与学习路径

### 5.1 GF 与其他框架对比

| 特性 | GameFramework | Entity Component System |
|------|---------------|------------------------|
| 资源管理 | ✅ 内置完整系统 | ❌ 需自行实现 |
| 对象池 | ✅ ReferencePool + ObjectPool | ✅ Entity 自带池化 |
| UI 系统 | ✅ 分层管理 UIGroup/UIForm | ❌ 通常用 UI Toolkit |
| 流程管理 | ✅ Procedure + FSM | ❌ 需自行实现 |
| 事件系统 | ✅ 内置 Event 模块 | ❌ 通常用自定义消息 |
| 适用场景 | 通用游戏开发 | ECS 高性能场景 |

### 5.2 学习路径建议

```
Step 1: 理解整体架构（三层模型）
    ↓
Step 2: 掌握核心入口 GameEntry + 组件注册机制
    ↓
Step 3: 学习事件系统（Subscribe/Fire 模式）
    ↓
Step 4: 掌握流程系统（Procedure 链）
    ↓
Step 5: 深入各模块（UI、Resource、Entity 等）
    ↓
Step 6: 实战：基于 TowerDefense/StarForce Demo 实践
    ↓
Step 7: 扩展：自定义 Helper、扩展模块
```

### 5.3 关键文件路径速查

| 模块 | 文件路径（官方仓库） |
|------|---------------------|
| 入口 | `Scripts/Runtime/Base/GameEntry.cs` |
| 组件基类 | `Scripts/Runtime/Base/GameFrameworkComponent.cs` |
| UI | `Scripts/Runtime/UI/UIComponent.cs`, `UIForm.cs`, `UIFormLogic.cs` |
| 事件 | `Scripts/Runtime/Event/EventComponent.cs` |
| 资源 | `Scripts/Runtime/Resource/ResourceComponent.cs` |
| 场景 | `Scripts/Runtime/Scene/SceneComponent.cs` |
| 实体 | `Scripts/Runtime/Entity/EntityComponent.cs` |
| 状态机 | `Scripts/Runtime/Fsm/FsmComponent.cs` |
| 流程 | `Scripts/Runtime/Procedure/ProcedureComponent.cs` |
| 对象池 | `Scripts/Runtime/ObjectPool/ObjectPoolComponent.cs` |
| 引用池 | `Scripts/Runtime/ReferencePool/ReferencePoolComponent.cs` |
| 配置 | `Scripts/Runtime/Config/ConfigComponent.cs` |
| 数据表 | `Scripts/Runtime/DataTable/DataTableComponent.cs` |
| 声音 | `Scripts/Runtime/Sound/SoundComponent.cs` |
| 网络 | `Scripts/Runtime/Network/NetworkComponent.cs` |
| 本地化 | `Scripts/Runtime/Localization/LocalizationComponent.cs` |
| 调试器 | `Scripts/Runtime/Debugger/DebuggerComponent.cs` |
| 下载 | `Scripts/Runtime/Download/DownloadComponent.cs` |
| 文件系统 | `Scripts/Runtime/FileSystem/FileSystemComponent.cs` |
| 设置 | `Scripts/Runtime/Setting/SettingComponent.cs` |
| 网络请求 | `Scripts/Runtime/WebRequest/WebRequestComponent.cs` |
| 变量 | `Scripts/Runtime/Variable/` (30 种变量类型) |

---

## 六、实践要点

### 6.1 事件链路完整示例

```csharp
// Manager 层：ConfigManager 通过 DataProvider 触发 ReadDataSuccess
// Component 层：ConfigComponent 监听 ReadDataSuccess → Fire LoadConfigSuccessEventArgs
// Game 层：ProcedurePreload 订阅 LoadConfigSuccess → 执行预加载逻辑
```

### 6.2 启动流程设计要点

```
ProcedureLaunch: 初始化构建信息、语言设置、本地化文本
    ↓
ProcedureSplash: 资源加载动画 + 加载方式判断
    ↓
ProcedureCheckVersion: 检查版本号
    ↓
ProcedureUpdateVersion: 下载版本资源
    ↓
ProcedureCheckResources: 确认需下载资源
    ↓
ProcedureUpdateResources: 下载资源
    ↓
ProcedurePreload: 预加载配置/字典/数据
    ↓
ProcedureLoadingScene: 切换场景
```

### 6.3 热更新配置

- BaseComponent: 取消 `EditorResourceMode`
- ResourceComponent: 设 `ResourceMode` 为 `Updatable`
- 打包配置: `BuiltinVersionListSerializer` 管理版本列表
- 部署测试: 使用 HFS 本地 HTTP 服务器模拟 CDN

---



## 七、数据结构与算法

### 7.1 图（Graph）

**基本概念**：一组顶点和边的集合。包括无向图/有向图、简单图、完全图、网（带权图）等。

**核心概念**：
- **顶点（Vertex）**：图中的数据元素
- **边（Edge）**：连接两个顶点的线，分无向边和有向边（弧）
- **度**：无向图中与顶点相连的边数；有向图中为入度+出度
- **路径**：顶点与边交替的非空序列
- **连通图**：任意两个顶点间都有路径

**存储结构**：
- **邻接矩阵**：用二维数组表示，适合稠密图，空间 O(n²)
- **邻接表**：用链表数组表示，适合稀疏图，空间 O(n+e)

**遍历算法**：
- **DFS（深度优先搜索）**：用递归或栈实现，沿一条路径深入到底再回溯
- **BFS（广度优先搜索）**：用队列实现，按层次逐层遍历

**典型应用**：路径规划、社交网络分析、编译器依赖图、游戏地图寻路（A*算法基于图）

---

### 7.2 树（Tree）

**基本概念**：
- **树叶**：没有子节点的节点
- **兄弟/兄弟节点**：有相同父节点的节点
- **深度**：从根到节点的路径长度
- **结点的度**：结点拥有的子树数目
- **二叉树**：每个节点最多两个子节点（左孩子和右孩子）
- **退化树**：每个非叶子节点只有一个孩子，等价于链表
- **有序树 vs 无序树**：子树次序是否重要
- **森林**：0个或多个不相交的树

**二叉树五种形态**：
1. 空集
2. 只有根节点
3. 根+左子树
4. 根+右子树
5. 根+左子树+右子树

**二叉树的遍历**：
- **前序（Pre-order）**：根 → 左 → 右
- **中序（In-order）**：左 → 根 → 右（二叉搜索树中序遍历得有序序列）
- **后序（Post-order）**：左 → 右 → 根
- **层序**：逐层从左到右

---

### 7.3 哈希表（HashTable）

**基本概念**：通过哈希函数将键（Key）映射到表中的位置，实现 O(1) 平均查找。

**核心要点**：
- **哈希函数**：将键值转换为数组索引
- **冲突处理**：开放寻址法、链地址法
- **应用**：C++ STL 的 unordered_map、Java HashMap、C# Dictionary 等

**例子**：手机通讯录按首字母分组，找"张三"直接跳到"Z"，无需遍历。

**负载因子**：表中元素数/表大小，超过阈值时需扩容（通常 ×2），触发 rehash。

---

### 7.4 线性表

**数组 vs 链表对比**：

| 操作 | 数组 | 链表 |
|------|------|------|
| 读取（随机访问） | O(1) | O(n) |
| 插入 | O(n) | O(1)（已知位置） |
| 删除 | O(n) | O(1)（已知位置） |
| 内存 | 连续分配，需预申请大小 | 分散分配，无需预申请 |
| 缓存命中率 | 高（局部性好） | 低（内存分散） |

**动态数组**：根据元素个数自动调整大小（如 C# List、Java ArrayList）

**栈（Stack）**：LIFO，只允许在一端操作（push/pop）
**队列（Queue）**：FIFO，先进先出（push at rear, pop at front）
**双端队列（Deque）**：两端均可入队和出队
**循环队列**：数组实现的队列，用取模运算实现循环

---

## 八、性能优化

### 8.1 UGUI 性能优化总结

**UGUI 基础**：
- **Canvas**：Unity Native 层组件，负责合批（Rebatch/Batch Build），标记 Dirty 时触发重建
- **Canvas Renderer**：将几何体数据提交到 Canvas
- **子 Canvas**：子 Canvas 被标记 Dirty 时不强制父 Canvas 重建，实现局部更新

**优化要点**：
1. **减少 Draw Call**：使用合批、减少 Canvas 数量、控制材质种类
2. **减少 Overdraw**：优化 UI 层级，避免不必要的透明叠加
3. **减少 GC**：避免每帧创建临时对象（字符串拼接、委托等），使用对象池
4. **Layout 优化**：减少动态布局计算，善用 Layout Group
5. **事件优化**：减少 EventTrigger 使用，用射线缓存

---

### 8.2 UWA 2020 Unity 手游性能蓝皮书（MMORPG）

**数据来源**：UWA 收集的 MMORPG 产品实际运行数据

**CPU 耗时分布**：

| CPU 耗时均值 (ms) | < 17 | 17-33 | 33-50 | > 50 |
|---|---|---|---|---|
| 占比 | 10% | 48% | 25% | 17% |

- Android 设备 CPU 均值主体范围：14.7~78.9ms
- **CPU 耗时占用分布**：渲染 36%、逻辑代码 32%、UI 9%、动画 6%、粒子 4%、物理 3%

**内存数据**：
- 低端设备：平均 ~280MB，主体范围 200-500MB
- 中端设备：平均 ~550MB，主体范围 300-900MB
- 高端设备：平均 ~720MB，主体范围 500-1200MB

**关键结论**：
- 渲染 + 逻辑代码占总 CPU 耗时的 68%，是优化重点
- 内存控制在 1GB 以下为健康状态
- 帧率稳定性比峰值帧率更重要（避免卡顿）

---

---

*文档整合了 gf 学习笔记、drflower.top 博客系列（GameFramework 10篇 + 数据结构与算法 4篇 + 性能优化 2篇）、TowerDefense Demo、DeepWiki (UnityGameFramework + StarForce) 的全部内容*
