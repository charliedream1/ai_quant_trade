## Warning: backend error   
- Error Context: Matplotlib is currently using agg, 
    which is a non-GUI backend, so cannot show the figure
- Solution:
  1. check available backend
  ``` python
  import matplotlib
  print(matplotlib.get_backend())
  ```
  2. select backend
  choose available backend from above, recommend 
  choosing 'Qt5Agg' or 'TkAgg'. Install if not missing package
  ``` shell
  pip3 install PyQt5
  ```
  There two options to config backend
  - set backend in the program
  ``` python
  import matplotlib
  import matplotlib.pyplot as plt
  matplotlib.use('Qt5Agg')  # Use Qt5Agg for plot show
  ```
  - set backend in the config file (not tested yet)   
  config file under path: C:\Users\pc\.matplotlib