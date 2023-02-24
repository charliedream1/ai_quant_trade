ERROR: Cannot uninstall ‘PyYAML’. It is a distutils installed project and thus 
we cannot accurately determine which files belong to it which would lead to only a partial uninstall.

问题描述：
在安装stable-baselines3的时候，报错“ERROR: Cannot uninstall ‘PyYAML’. 
It is a distutils installed project and thus we cannot accurately determine 
which files belong to it which would lead to only a partial uninstall.”

问题解决：
1. 方法1
   只需要将原安装命令，修改成：
   ```
   pip install stable-baselines3 stable-baselines3
   ```
   
2. 方法2
    搜索找到PyYAML的路径，然后删除。
    ```
     1. 服务器是ububtu18.04，site-packages文件夹路径在 /anaconda3/lib/python3.6/site-packages
     2. win10下路径：anaconda3\Lib\site-packages
    ```
