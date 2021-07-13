## 心智分类器

该文件夹包含思维分类器的脚本。

### 训练

1. 运行`main()`中`annotation_clean_saved_att.py`得到不同的基线数据。
2. 事件先验使用`distribution_cal.py`计算。
3. 思维先验使用`get_mind_distribution.py`计算。
4. 运行`mind_training_combined.py`训练。

### 测试

1. 可以在[此处](https://github.com/LifengFan/Triadic-Belief-Dynamics/blob/main/src/mind_classfier/xxxx)找到预训练模型并将其放入 ./cptk
2. 可以在[此处](https://github.com/LifengFan/Triadic-Belief-Dynamics/blob/main/src/mind_classfier/xxxx)找到搜索到的事件树并将其放入
   ./BestTree/
3. 在`get_mind_posterior_ours_saved_att.py`中运行`test_raw_data()`对检测到的对象进行推理。
4. 在`get_mind_posterior_ours_saved_att.py`中运行`get_gt_data()`对带注释的对象进行推理。
5. 在`get_mind_posterior_ours_saved_att.py`中运行`result_eval()`和`save_roc_plot()`以可视化结果。



