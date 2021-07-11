## 数据处理脚本

该文件夹包含用于数据处理的脚本，包括对象检测、对象跟踪、从深度图像获取点云、眼动仪注视估计

### 物体检测

1. 按照[Detectron 2](https://github.com/facebookresearch/detectron2)上的说明安装必要的库
2. 运行`python detectron2_img_detect_kinect.py --data-path`以提取对象边界框、蒙版和结果视频

### 对象跟踪

1. 按照[Deep SORT](https://github.com/nwojke/deep_sort)上的说明安装必要的库
2. 通过运行运行更改对象检测到深排序所需的格式的结果`python obj_reformat.py`和`python deep_sort_generate_detections.py --model --mot_dir --output_dir`
3. 运行`python deep_sort_tracker.py --data_path --detection_file --output_path`获取对象跟踪结果

### 对象跟踪平滑

详细解释请参考`box_smooth.py`中的main()

### 来自深度图像的点云

使用从`detectron2`和深度图像中估计的对象掩码，我们将通过运行来估计每个对象的3D中心 `python pointclouds.py`

### 眼动仪注视估计

由于眼球追踪器对 2D 第一视图图像具有精确地注视估计，我们希望通过基于对象的颜色和类别在第一视图和第三视图之间找到对应的对象来估计 3D 注视方向。然后对象的 3D 中心（从点云估计）和人头中心（从骨架估计）之间的差异可以被视为 3D 空间中的注视方向。详细信息可以在`view_mapping.py`
