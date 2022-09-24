## Error: Plot Not Response
- Problem: Pop out plot window is empty and not response
- Solution: There might be environment conflicts, 
  set as below
 ``` python
 plt.show(block=True)
 ```