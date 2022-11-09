要卸载Anaconda，您可以简单地删除该程序。这将留下一些文件，对于大多数用户来说就足够了。请参阅选项A。

如果您还想从Anaconda及其程序中删除配置文件和目录的所有痕迹，则可以先下载并使用Anaconda-Clean程序，然后进行简单的删除。请参阅选项B。

 
1、选项A.使用简单删除来卸载Anaconda：

* Windows系统   
在安装根目录中运行卸载之前，请使用Windows资源管理器删除envs和pkgs文件夹。
在“控制面板”中，选择“添加或删除程序”或“卸载程序”，然后选择“ Python 3.6（Anaconda）”或您的Python版本。
* 苹果系统  
打开Terminal.app或iTerm2终端应用程序，然后删除整个阿纳康达目录，它有一个名称，例如anaconda2，anaconda3，或~/opt。输入以删除目录。rm -rf ~/anaconda3
* Linux系统  
打开一个终端窗口，然后通过输入删除整个Anaconda目录，该目录的名称为anaconda2或。anaconda3rm -rf ~/anaconda3
 

2、选项B.使用Anaconda-Clean完全卸载并简单删除。  
注意：必须先运行Anaconda-Clean，然后才能将其删除。

 
从Anaconda Prompt（Linux或macOS上的终端）安装Anaconda-Clean软件包：
```bash
conda install anaconda-clean
```
在同一窗口中，运行以下命令之一：

在删除每个与Anaconda相关的文件和目录之前，请先确认确认，然后删除每个文件和目录：
```bash
anaconda-clean
```
或者，删除所有与Anaconda相关的文件和目录，而不会提示您删除每个文件和目录：

```bash
anaconda-clean --yes
```
Anaconda-Clean创建所有文件和目录的备份，这些文件和目录可能会.anaconda_backup在主目录中命名的文件夹中删除。还要注意，Anaconda-CleanAnacondaProjects目录中的数据文件保持不变。

使用Anaconda-Clean之后，请按照上述选项A中的说明卸载Anaconda。

从.bash_profile中删除Anaconda路径
如果您使用的是Linux或macOS，则还可能希望检查.bash_profile主目录中的文件是否存在以下行：

```bash
export PATH="/Users/jsmith/anaconda3/bin:$PATH"
```
 
注意：替换/Users/jsmith/anaconda3/为您的实际路径。

此行将Anaconda路径添加到PATH环境变量中。它可能指的是Anaconda或Miniconda。卸载Anaconda后，您可以删除此行并保存文件。

卸载Anaconda  
1、选项A.使用简单删除来卸载Anaconda：
2、选项B.使用Anaconda-Clean完全卸载并简单删除。
从.bash_profile中删除Anaconda路径


来源：https://www.cnblogs.com/zhif97/p/12099903.html#:~:text=%E6%89%93%E5%BC%80%E4%B8%80%E4%B8%AA%E7%BB%88%E7%AB%AF%E7%AA%97%E5%8F%A3%EF%BC%8C%E7%84%B6%E5%90%8E%E9%80%9A%E8%BF%87%E8%BE%93%E5%85%A5%E5%88%A0%E9%99%A4%E6%95%B4%E4%B8%AAAnaconda%E7%9B%AE%E5%BD%95%EF%BC%8C%E8%AF%A5%E7%9B%AE%E5%BD%95%E7%9A%84%E5%90%8D%E7%A7%B0%E4%B8%BAanaconda2%E6%88%96%E3%80%82%20anaconda3rm,-rf%20~%2Fanaconda3%202%E3%80%81%E9%80%89%E9%A1%B9B.%E4%BD%BF%E7%94%A8Anaconda-Clean%E5%AE%8C%E5%85%A8%E5%8D%B8%E8%BD%BD%E5%B9%B6%E7%AE%80%E5%8D%95%E5%88%A0%E9%99%A4%E3%80%82
