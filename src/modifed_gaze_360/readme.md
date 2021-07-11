## 修改后的凝视 360

该文件夹包含用于注视预测的脚本。我们使用来自眼动仪的 3D 凝视方向估计作为基本事实并微调凝视 360 模型。然后训练好的模型将用于对佩戴 Pivothead 眼镜的人进行注视预测。

### 训练

1. 可以使用` test_gaze_360.py` 中的` record_skeleton_for_training() `生成训练数据
2. 跑步`python run_skele.py`训练

### 推理

使用` test_gaze_360.py` 中的` Gaze360_estimation() `来预测佩戴 Pivothead 眼镜的人的视线

### 目光平稳

在注视预测之后，我们对丢失的帧进行插值。详细信息可以在 `main()gaze_smooth.py `中找到

