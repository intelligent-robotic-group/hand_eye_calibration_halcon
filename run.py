"""
written by ryanreadbooks
date: 2021/11/11
function: 生成可以直接运行的halcon文件，不用每次都手动修改相关内容
"""

import argparse
import glob
import os
import pathlib
import copy
import re
import sys
import xml.etree.ElementTree as ET
import shutil


USAGE_DESCRIPTION = '处理图片和位姿文件，直接生成Halcon能运行的手眼标定脚本。'
N_NUM = 3

parser = argparse.ArgumentParser(usage=USAGE_DESCRIPTION)
parser.add_argument('--eye_on_hand', default=False, action='store_true', dest='eye_on_hand',
                    help='选择使用眼在手上的标定方式')
parser.add_argument('-i', '--img-dir', type=str, dest='img_dir', required=True,
                    help='指定图片所在文件夹，文件夹中的图片将会按照默认排序进行处理，所以文件夹中的图片需要按照序号排序；')
parser.add_argument('-p', '--pose-path', type=str, dest='pose_path', required=True,
                    help='指定每张图片对应的机械臂末端位姿的txt文件路径，文件中每行代表一个位姿，需要和文件夹中的图片顺序一一对应；'
                         '格式：前三个只为末端位置，单位（m），后三个值为末端姿态，单位（度）；每个值之间用英文逗号分隔'
                         '每行用回车分隔')
parser.add_argument('-c', '--camera', type=str, dest='camera', required=True,
                    choices=['d415', 'd435i'],
                    help='指定用的是哪个相机，可选值（d415, d435i）')
parser.add_argument('-o', '--output-dir', dest='out_dir', required=True,
                    help='指定输出路径，输出结果是文件夹形式')
args = parser.parse_args()


def pretty_xml(element, indent, newline, level=0):
    # 判断element是否有子元素
    if element:

        # 如果element的text没有内容
        if element.text is None or element.text.isspace():
            element.text = newline + indent * (level + 1)
        else:
            element.text = newline + indent * (level + 1) + element.text.strip() + newline + indent * (level + 1)

    # 此处两行如果把注释去掉，Element的text也会另起一行
    # else:
    # element.text = newline + indent * (level + 1) + element.text.strip() + newline + indent * level

    temp = list(element)  # 将elemnt转成list
    for subelement in temp:
        # 如果不是list的最后一个元素，说明下一个行是同级别元素的起始，缩进应一致
        if temp.index(subelement) < (len(temp) - 1):
            subelement.tail = newline + indent * (level + 1)
        else:  # 如果是list的最后一个元素， 说明下一行是母元素的结束，缩进应该少一个
            subelement.tail = newline + indent * level

            # 对子元素进行递归操作
        pretty_xml(subelement, indent, newline, level=level + 1)


def gen_create_pose_hdev(poses, eye_on_hand=False):
    def create_line(parent, text):
        l = ET.SubElement(parent, 'l')
        l.text = text

    root = ET.Element('hdevelop', {'file_version': '1.1', 'halcon_version': '17.12'})
    procedure = ET.SubElement(root, 'procedure', {'name': 'main'})
    ET.SubElement(procedure, 'interface')
    body = ET.SubElement(procedure, 'body')

    for i, pose in enumerate(poses):
        pose_str = ','.join(pose)
        code1 = f"create_pose ({pose_str}, 'Rp+T', 'abg', 'point', Pose2)"
        if not eye_on_hand:
            code2 = f"write_pose (Pose2, 'campose{str(i).zfill(N_NUM)}.dat')"
        else:
            code2 = f"write_pose (Pose2, 'robot_pose_{str(i).zfill(N_NUM)}.dat')"
        create_line(body, code1)
        create_line(body, code2)

    docu = ET.SubElement(procedure, 'docu', {'id': 'main'})
    ET.SubElement(docu, 'parameters')
    if sys.platform == 'linux':
        pretty_xml(root, '\t', '\n')
    elif sys.platform == 'win32':
        pretty_xml(root, '\t', '\r\n')
    tree = ET.ElementTree(root)

    return tree


def gen_hand_eye_cali_hdev(n_img, camera, eye_on_hand=False):
    if not eye_on_hand:
        # 眼在手外
        tree = ET.parse('templates/hand_eye_stationarycam_calibration.hdev')
    else:
        # 眼在手上
        tree = ET.parse('templates/hand_eye_movingcam_calibration.hdev')
    root = tree.getroot()
    all_line_elem = root.find('procedure').find('body').findall('l')
    for line in all_line_elem:
        # 设置图片数量
        if line.text.__contains__('NumImages := '):
            line.text = f'NumImages := {n_img}'
        elif line.text.__contains__("read_image (Image, ImageNameStart + '00'"):
            line.text = f"read_image (Image, ImageNameStart + '{str(0).zfill(N_NUM)}')"
        elif line.text.__contains__('read_cam_par'):
            cam_param = 'D435i-HC80.dat' if camera == 'd435i' else 'D415-HC80.dat'
            line.text = f"read_cam_par (DataNameStart + '{cam_param}', StartCamParam)"

    xml_string = str(ET.tostring(element=tree.getroot(), encoding='UTF-8'), encoding='utf-8')
    xml_string = xml_string.replace("02d", f"0{N_NUM}d")
    root = ET.fromstring(xml_string)

    return ET.ElementTree(root)


def main():
    # 重命名每张图片
    img_names = sorted(glob.glob(os.path.join(args.img_dir, '*.png')))
    if len(img_names) == 0:
        img_names = sorted(glob.glob(os.path.join(args.img_dir, '*.jpg')))
        if len(img_names) == 0:
            raise ValueError('指定文件夹不存在.png或者.jpg的图片！')
    print(f'共有{len(img_names)}张图片')
    # 重命名所有图片成格式
    print('重命名图片...')
    images_paths = []
    for i, img_name in enumerate(img_names):
        new_pathname = pathlib.Path(img_name)
        new_name = copy.deepcopy(img_name).replace(new_pathname.stem, f'image_{str(i).zfill(N_NUM)}')
        new_pathname.rename(new_name)  # 重命名文件
        images_paths.append(new_name)
        print(img_name, ' => ', new_name)
    # 从位姿文件中提取机器人对应的末端位姿
    print(f'现在处理位姿文件{args.pose_path}...')
    poses = []
    with open(args.pose_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not len(line) == 0:
                pose = re.split(',|, ', line)
                poses.append(pose)
                print('==> ', pose)

    if len(poses) != len(img_names):
        raise ValueError('图片的数量和位姿的数量不对应！')

    # 生成Halcon脚本
    print('现开始生成Halcon脚本...')
    # 生成pose的hdev脚本
    hdev_file_gen_pose = gen_create_pose_hdev(poses, args.eye_on_hand)
    # 生成标定的hdev脚本
    hdev_file_cali_handeye = gen_hand_eye_cali_hdev(len(poses), args.camera, args.eye_on_hand)

    if not os.path.exists(args.out_dir):
        os.makedirs(os.path.join(args.out_dir, 'img'))
    hdev_outdir1 = os.path.join(args.out_dir, 'gen_pose_matrix.hdev')
    hdev_outdir2 = os.path.join(args.out_dir, 'hand_eye_cam_calibration.hdev')
    hdev_file_gen_pose.write(hdev_outdir1, encoding='UTF-8', xml_declaration=True)
    hdev_file_cali_handeye.write(hdev_outdir2, encoding='UTF-8', xml_declaration=True)

    # 图片复制过去
    dest_path = os.path.join(args.out_dir, 'img')
    if not os.path.exists(dest_path):
        os.makedirs(dest_path)
    print(f'复制图片到路径 {dest_path}')
    for img_path in images_paths:
        shutil.copy2(img_path, dest_path)
    # 对应的相机内参文件复制到输出文件夹中
    cam_file = 'templates/D415-HC80.dat' if args.camera == 'd415' else 'templates/D435i-HC80.dat'
    shutil.copy2(cam_file, args.out_dir)
    # 标定板的描述文件复制到输出文件夹中
    shutil.copy2('templates/HC-IW.descr', args.out_dir)
    print('处理完成')


if __name__ == '__main__':
    main()
