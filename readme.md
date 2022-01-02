

# Halcon手眼标定过程中数据处理

### 该脚本用于处理实验室Halcon手眼标定的数据。

---

### 功能：
* 生成gen_pose_matrix.hdev脚本，该脚本用来生成Halcon可识别的位姿文件
* 生成hand_eye_cam_calibration.hdev脚本，该脚本用来执行手眼标定操作(眼在手上和眼在手外均支持)

### 用法

#### **1、前提：**

* 已经拍摄了带有标定板的图片8～10张
* 每张图片都记录了MA2010对应末端的位姿，并且写在一个txt文件里面；

**2、运行run.py**：

```bash
# 眼在手外
python run.py -i 拍摄的图片路径 -p 位姿文本文件的路径 -c 用哪个相机拍的图片 -o 最终结果输出路径
# 眼在手上
python run.py --eye_on_hand -i 拍摄的图片路径 -p 位姿文本文件的路径 -c 用哪个相机拍的图片 -o 最终结果输出路径
```

**查看每个参数的含义：**

```bash
python run.py --help 
```

#### 3、在Halcon中分别运行gen_pose_matrix.hdev和hand_eye_cam_calibration.hdev

* 先执行gen_pose_matrix.hdev将记录的位姿文本文件转换Halcon格式
* 再执行hand_eye_cam_calibration.hdev进行手眼标定得到结果

