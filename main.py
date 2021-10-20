# coding=utf-8
import logging
import os
import shutil
import sys
import numpy as np
import cv2
import wx

reload(sys)
sys.setdefaultencoding('utf-8')

'''
    使用说明：
    1 python main.py +需要标记的文件夹路径path。
    2 图片显示出来后点击一下图片确保焦点在图片窗口上
    3 使用按键进行标记操作
        ESC： 退出
        ENTER： 标记为正确
        n： 标记为非标准图片，标记后图片会被移到path下的not_standard文件夹
        e： 标记为错误分类，标记后图片会被移到path下的error文件夹
        空格：先跳过这一张
    4 结束后可以查看mark_state.txt来查看各个文件的标记状态，下次再次启动会加载已有的标记文件
    
'''
# 设置调试信息等级
logging.basicConfig(level=logging.INFO)

mark_file_name = 'mark_state.txt'
non_standard_name = 'not_standard'
error_name = 'error'
valid_types = ['jpg', 'jpeg', 'png']
total_number = 0  # 统计有效文件总数
not_handle_number = 0  # 统计未处理数量
new_correct_num = 0  # 统计本次新标记为正确数
new_error_num = 0  # 统计本次新标记为错误分类数
new_not_standard_num = 0  # 统计本次新标记为非标准数


def prepare_dir(path):
    # 判断error和non_standard文件夹是否存在，不存在则创建
    non_standard_path = os.path.join(path, non_standard_name)
    if not os.path.exists(non_standard_path):
        os.makedirs(non_standard_path)
    error_path = os.path.join(path, error_name)
    if not os.path.exists(error_path):
        os.makedirs(error_path)


def load_state(path, mark_file_name):
    mark_file_path = os.path.join(path, mark_file_name)
    # 获取文件夹下的所有图片文件
    walking = os.walk(path)
    valid_files = []
    for path, dir_list, file_list in walking:
        for file_name in file_list:
            file_type = file_name.split('.')[-1]
            if file_type in valid_types:
                valid_files.append(file_name)
    # logging.debug("找到的文件:\n{}".format(valid_files))
    global total_number, not_handle_number
    total_number = len(valid_files)
    data = {}
    # 判断标注文件是否存在
    if os.path.exists(mark_file_path):
        print("找到标注状态文件，加载已有文件")
        f1 = open(mark_file_path, "r")
        lines = f1.readlines()
        logging.debug("读取到的状态文件内容:{}".format(lines))
        for line in lines:
            items = line.strip('\n').split('====')
            if len(items) < 4:
                logging.error("标注文件格式异常:{}".format(line))
                continue  # 遇到异常行先跳过
            name, result, mark_state, file_state = items[0:4]
            if name in valid_files:
                data[name] = {'result': result, 'mark_state': mark_state, 'file_state': 'file_normal'}
                valid_files.remove(name)
                global not_handle_number
                if str(mark_state) == '0':
                    not_handle_number = not_handle_number + 1
            else:
                data[name] = {'result': result, 'mark_state': mark_state, 'file_state': 'file_not_exist'}
        # logging.debug("加载已有状态信息结果：{}".format(data))
        f1.close()
    else:
        not_handle_number = total_number
        logging.info("未找到标注状态文件，将创建新文件")
    for name in valid_files:
        data[name] = {'result': 'unknown', 'mark_state': '0', 'file_state': 'file_normal'}
    return data


def save_and_exit(path, data):

    try:
        temp_file = os.path.join(path, 'bak_' + mark_file_name)
        mark_file_path = os.path.join(path, mark_file_name)
        with open(temp_file, "w+") as f1:
            for name in data.keys():
                info = data[name]
                f1.write("{}===={}===={}===={}\n".format(name, info['result'], info['mark_state'], info['file_state']))
            f1.close()
        if os.path.exists(mark_file_path):
            os.remove(mark_file_path)
        os.rename(temp_file, mark_file_path)
        logging.info("已经成功保存标注文件")
        sys.exit()
    except Exception as e:
        logging.error("保存文件时碰到异常:{}".format(e))


def print_progress():
    global total_number, new_error_num, new_correct_num, new_not_standard_num, not_handle_number
    logging.info("====  标记进度： 文件数:{} 未标记数：{} 本次新标记正确数：{}  本次新标记非标准数：{} 本次标记错误分类数:{}"
                 .format(total_number, not_handle_number, new_correct_num, new_not_standard_num, new_error_num))


def mark_pic(path, data):
    try:
        cv2.namedWindow("Mark Image")
        for name in data.keys():
            info = data[name]
            print("name: {} info:{}".format(name, info))  # TODO
            if str(info['mark_state']) == '0' and info['file_state'] == 'file_normal':
                img =  img=cv2.imdecode(np.fromfile(os.path.join(path, name), dtype=np.uint8),cv2.IMREAD_COLOR)
                # img = cv2.imread(os.path.join(path, name))
                cv2.imshow("Mark Image", img)
                while True:
                    key = cv2.waitKey(0)
                    logging.debug("key = {}".format(key))
                    try:
                        if key == 27:  # ESC
                            logging.info("按下Esc键，保存并退出{}")

                            print_progress()
                            save_and_exit(path, data)
                        elif key == 13:
                            logging.info("按下Enter键，标注为正常 {}".format(name))
                            data[name]['result'] = 'ok'
                            data[name]['mark_state'] = '1'
                            data[name]['file_state'] = 'file_normal'
                            global new_correct_num, not_handle_number
                            new_correct_num = new_correct_num + 1
                            not_handle_number = not_handle_number - 1
                            print_progress()
                            break
                        elif key == 32:
                            logging.info("按下空格键,先跳过{}".format(name))
                            break  # 先跳过到下一张
                        elif key == 110:
                            logging.info("按下n键，{}图片移动到not_standard".format(name))
                            shutil.move(os.path.join(path, name), os.path.join(path, non_standard_name, name))
                            data[name]['result'] = 'move_to_not_standard'
                            data[name]['mark_state'] = '2'
                            data[name]['file_state'] = 'file_not_exist'
                            global new_not_standard_num
                            global not_handle_number
                            new_not_standard_num = new_not_standard_num + 1
                            not_handle_number = not_handle_number - 1
                            print_progress()
                            break  # 先跳过到下一张
                        elif key == 101:
                            logging.info("按下e键，{}图片移动到error".format(name))
                            shutil.move(os.path.join(path, name), os.path.join(path, error_name, name))
                            data[name]['result'] = 'move_to_error'
                            data[name]['mark_state'] = '3'
                            data[name]['file_state'] = 'file_not_exist'
                            global new_error_num
                            global not_handle_number
                            new_error_num = new_error_num + 1
                            not_handle_number = not_handle_number - 1
                            print_progress()
                            break  # 先跳过到下一张
                        else:
                            logging.info("未知按键，请重新操作 key:{}, 操作说明：\nENTER：标注ok \n空格：先跳过\nn：非标准\ne：错误分类图\n".format(key))
                            continue
                    except Exception as e:
                        logging.error(e)
                        continue
            else:
                logging.info("图片已处理，跳过:{}".format(name))
        cv2.destroyAllWindows()
    except Exception as e:
        logging.error(e)
    finally:
        save_and_exit(path, data)


def show_img_and_confirm(path):
    prepare_dir(path)
    data = load_state(path, mark_file_name)
    print_progress()
    mark_pic(path, data)


def main(argv):
    path = os.getcwd()
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if not os.path.exists(path):
            logging.error("路径不存在，请确认：{}".format(path))
            sys.exit(2)
        if not os.path.isdir(path):
            logging.error("路径类型不是文件夹，请确认：{}".format(path))
            sys.exit(2)
        # 加一个更新功能
        show_img_and_confirm(path)
        logging.info(" !!!!!!!! 恭喜您，您已完成当前文件夹下的所有标注 !!!!!!!!!")
    else:
        logging.error("未指定标注文件夹路径,使用示范为 python main.py /Users/username/pic_dir")
        sys.exit(2)


if __name__ == '__main__':
    # Marker(sys.argv[1:])
    main(sys.argv[1:])
