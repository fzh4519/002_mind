## 数据处理脚本

该文件夹包含用于数据处理的脚本，包括对象检测、对象跟踪、从深度图像获取点云、眼动仪注视估计

### 物体检测

1. 按照[Detectron 2](https://github.com/facebookresearch/detectron2)上的说明安装必要的库
2. 运行`python detectron2_img_detect_kinect.py --data-path`以提取对象边界框、蒙版和结果视频

### 对象跟踪

1. 按照[Deep SORT](https://github.com/nwojke/deep_sort)上的说明安装必要的库
2. 通过运行`obj_reformat.py`和`python deep_sort_generate_detections.py --model --mot_dir --output_dir`将对象检测结果更改为深度排序所需的格式
3. 运行`deep_sort_tracker.py --data_path --detection_file --output_path`获取对象跟踪结果

### 对象跟踪平滑

详细解释请参考`box_smooth.py`中的main()

### 来自深度图像的点云

使用从`detectron2`和深度图像中估计的对象掩码，通过运行 `python pointclouds.py`来估计每个对象的3D中心

### 眼动仪注视估计

由于眼动仪对2D第一视图图像有精确的注视估计，所以我们想通过根据物体的颜色和类别找到第一视图和第三视图之间对应的物体来估计3D的注视方向。然后将物体的三维中心(由点云估计)与人头中心(由骨架估计)之间的差值作为三维空间中的注视方向。详细信息可以在view mapping.py中找到