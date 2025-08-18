# Packnload
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
### mod列表(mod_list)注:
一行一个(开头和结尾要双引号且如果下行还有结尾需要逗号)  
是modrinth的模组slug  
比如Sodium的URL是"https://modrinth.com/mod/sodium"  
就是跟在"/mod/"后面的那串(sodium)  
但是如果结尾有/要去掉  
比如URL为"https://modrinth.com/mod/sodium/" ,那么结果不是sodium/  
要把结尾的/去掉,所以结果应该是sodium  
