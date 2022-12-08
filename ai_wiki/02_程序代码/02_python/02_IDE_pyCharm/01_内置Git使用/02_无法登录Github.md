![](.02_无法登录Github_images/Github链接报错.png)

显示如图错误。
在github中：右上角头像-> settings --> Developer settings -->Personal access tokens --> Generate new token，创建新的token

Token创建权限选择，选择有效期，一般全选就行
![](.02_无法登录Github_images/Token创建权限选择.png)

![](.02_无法登录Github_images/TOKEN生成页面.png)
复制这个token，使用token登录

打开PyCharm,进入 File -> Settings-> Version Control -> GitHub，点击右上角 + 号
![设置页面](.01_登录Github_images/设置页面.png)

选择 Log In via Token
![登录Github按钮](.01_登录Github_images/登录Github按钮.png)

我们可以看到我们GitHub账号已经成功添加到PyCharm
![](.01_登录Github_images/pyCharm中Github登录成功.png)
