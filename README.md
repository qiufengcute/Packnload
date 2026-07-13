# <img src="icon.ico" width="16" height="16" /> Packnload
![MIT](https://img.shields.io/badge/License-MIT-blue.svg)

**一款轻量级、高效的 Minecraft Mod 批量下载工具**

Packnload 可以帮助你快速下载 `.modpack` 文件中的所有模组，支持指定游戏版本和加载器，同时提供暂停、继续、取消下载功能，还可以将下载好的模组打包成 ZIP 文件，方便分发或备份。

---

## 功能特性

* 📦 **批量下载 Mod**
  从 `.modpack` 文件中读取模组列表，一键下载所有模组。

* ⚡ **支持暂停/继续/取消**
  下载过程中可随时暂停或取消，无需重启程序。

* 🎯 **支持游戏版本 & 加载器筛选**
  支持 `fabric`、`forge`、`quilt`、`neoforge`，可指定 Minecraft 游戏版本。

* 🗂️ **自动整理文件**
  可以选择直接存储模组或打包成 ZIP 文件。

* 🧩 **查看模组列表**
  快速查看 `.modpack` 内包含的模组 ID。

---

## 快速开始 

1. 下载最新版本 Release 中的 `Packnload.exe`
2. 运行 `Packnload.exe` 

---

## 使用方法

1. **选择 .modpack 文件**
   点击“选择文件”，载入你的 `.modpack` 文件。

2. **填写游戏版本与加载器**
   例如游戏版本 `1.21.1`，加载器选择 `fabric`。

3. **选择模组存储路径**
   下载的模组将会存放在此目录。

4. **是否打包 ZIP**
   勾选可将所有模组打包成 ZIP 文件。

5. **开始下载**
   点击“开始下载”，可在下载过程中暂停、继续或取消。

6. **查看下载结果**
   下载完成后，程序会提示下载失败的模组列表（如有）。

## .modpack文件格式
```
{
    "name":"模组包名",
    "author":"作者名",
    "version":"版本号",
    "mod_list":[
        "mod列表"
    ]
}
```

---

### `mod_list` 填写说明

`mod_list` 中的每一项可以是 **普通字符串**（单个模组），也可以是 **字符串数组**（多个备选模组）。

#### 1. 普通格式（单个模组）

直接填写 Modrinth 上的模组 slug，即 Modrinth 页面 URL 中 `/mod/` 后面的部分。

**示例：**  
- Sodium 的 Modrinth 页面为：`https://modrinth.com/mod/sodium` → slug 为 `sodium`  
- 如果 URL 末尾带有斜杠，如 `https://modrinth.com/mod/sodium/`，请去掉末尾的 `/`，结果仍为 `sodium`

```json
"mod_list": [
    "sodium",
    "iris"
]
```

---

#### 2. 备选格式（多个候选模组）

如果某个模组有多个候选 slug（例如不同作者发布的版本、不同分支或镜像源），可以用 **数组** 将多个 slug 写在同一项中。

**格式：**  
`["候选1", "候选2", "候选3", ...]`

**下载逻辑：**  
程序会按数组顺序依次尝试下载：  
- 候选1 成功 → 使用该模组，跳过后续候选；  
- 候选1 失败 → 自动尝试候选2；  
- 候选2 失败 → 继续尝试候选3，依此类推；  
- 全部失败 → 该模组最终标记为下载失败。

**示例：**

```json
"mod_list": [
    "sodium",
    ["fabric-api", "fabric-api-fallback"],
    "iris",
    ["optifine", "optifine-alt", "optifine-mirror"]
]
```

上述示例中：
- `sodium` 和 `iris` 为普通单项，直接下载；
- `fabric-api` 优先尝试 `fabric-api`，失败则尝试 `fabric-api-fallback`；
- `optifine` 依次尝试三个候选，直到成功或全部失败。
