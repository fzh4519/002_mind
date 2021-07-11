import numpy as np
import torch
from torch.autograd import Variable
import pickle

from torch.optim.lr_scheduler import MultiStepLR
from tqdm import tqdm
import os
from sklearn import metrics
import glob
from annotation_clean import *
from sklearn import svm
import matplotlib.pyplot as plt
import joblib
from mind_model import *
import seaborn as sn
import random
from torchvision import transforms
import cv2
import sys
sys.path.append('/home/shuwen/data/Six-Minds-Project/data_processing_scripts/')
from metadata import *
from utils import *

def plot_confusion_matrix(cmc):
    df_cm = pd.DataFrame(cmc, range(cmc.shape[0]), range(cmc.shape[1]))
    sn.set(font_scale=1.4)  # for label size
    sn.heatmap(df_cm, annot=True, annot_kws={"size": 16})  # font size
    plt.show()

def calculate_dis(data_path, model_type):
    clips = os.listdir(data_path)
    train_x = {'mc':[0, 0, 0, 0], 'm1':[0, 0, 0, 0], 'm2':[0, 0, 0, 0], 'm12':[0, 0, 0, 0], 'm21':[0, 0, 0, 0]}
    test_x = {'mc': [0, 0, 0, 0], 'm1': [0, 0, 0, 0], 'm2': [0, 0, 0, 0], 'm12': [0, 0, 0, 0], 'm21': [0, 0, 0, 0]}
    for clip in clips:
        print(clip)
        with open(data_path + clip, 'rb') as f:
            if model_type == 'single' or model_type == 'single_one_hot':
                vec_input, label_, _ = pickle.load(f)
            else:
                vec_input, label_ = pickle.load(f)

            for lid, label in enumerate(label_):
                label = label.reshape(-1)
                labels_mc = np.argmax(label[:4])
                labels_m21 = np.argmax(label[4:8])
                labels_m12 = np.argmax(label[8:12])
                labels_m1 = np.argmax(label[12:16])
                labels_m2 = np.argmax(label[16:20])

                if clip in mind_test_clips:
                    test_x['mc'][labels_mc] += 1
                    test_x['m1'][labels_m1] += 1
                    test_x['m2'][labels_m2] += 1
                    test_x['m12'][labels_m12] += 1
                    test_x['m21'][labels_m21] += 1
                else:
                    train_x['mc'][labels_mc] += 1
                    train_x['m1'][labels_m1] += 1
                    train_x['m2'][labels_m2] += 1
                    train_x['m12'][labels_m12] += 1
                    train_x['m21'][labels_m21] += 1
    print(train_x)
    print(test_x)

def get_data(data_path, model_type):

    clips = os.listdir(data_path)
    data = []
    labels = []

    sep_data = {0:[], 1:[], 2:[], 3:[], 4:[]}
    sep_label = {0:[], 1:[], 2:[], 3:[], 4:[]}
    for clip in clips:
        print(clip)
        with open(data_path + clip, 'rb') as f:
            if model_type == 'single' or model_type == 'single_one_hot' or model_type == 'tree_search' or model_type == 'event_memory':
                vec_input, label_, _ = pickle.load(f)
            else:
                vec_input, label_ = pickle.load(f)
            data = data + vec_input
            labels = labels + label_
            for lid, label in enumerate(label_):
                label = label.reshape(-1)
                if label[0] == 1 or label[4] == 1 or label[8] == 1 or label[12] == 1 or label[16] == 1:
                    sep_data[0].append(vec_input[lid])
                    sep_label[0].append(label)
                if label[1] == 1 or label[5] == 1 or label[9] ==  1 or label[13] == 1 or label[17] == 1:
                    sep_data[1].append(vec_input[lid])
                    sep_label[1].append(label)
                if label[2] == 1 or label[6] == 1 or label[10] == 1 or label[14] == 1 or label[18] == 1:
                    sep_data[2].append(vec_input[lid])
                    sep_label[2].append(label)
                if label[3] == 1 or label[7] == 1 or label[11] == 1 or label[15] == 1 or label[19] == 1:
                    sep_data[3].append(vec_input[lid])
                    sep_label[3].append(label)


    sep_train_x, sep_train_y = {}, {}
    test_x, test_y = [], []
    for i in sep_data.keys():
        if i == 4:
            continue
        data = sep_data[i]

        label = sep_label[i]
        c = list(zip(data, label))
        random.shuffle(c)
        ratio = len(c) * 0.8
        ratio = int(ratio)
        data, label = zip(*c)

        label = np.array(label)

        train_x, train_y = data[:ratio], label[:ratio]
        test_xs, test_ys = data[ratio:], label[ratio:]
        sep_train_x[i] = train_x
        sep_train_y[i] = train_y

        test_x.extend(test_xs)
        test_y.extend(test_ys)

    print(len(test_x), len(test_y))

    max_sample = max(len(sep_train_x[0]), len(sep_train_x[1]), len(sep_train_x[2]), len(sep_train_x[3]))

    train_x, train_y = [], []
    for i in sep_train_x.keys():
        repeat_time = int(max_sample/len(sep_train_x[i]))

        if not i == 3:
            for j in range(repeat_time):
                train_x.extend(sep_train_x[i])
                train_y.extend(sep_train_y[i])

    c = list(zip(train_x, train_y))
    random.shuffle(c)
    ratio = len(c) * 0.75
    ratio = int(ratio)
    data, label = zip(*c)

    train_x, train_y = data[:ratio], label[:ratio]
    validate_x, validate_y = data[ratio:], label[ratio:]
    return train_x, train_y, validate_x, validate_y, test_x, test_y

class mydataset_event_mem(torch.utils.data.Dataset):
    def __init__(self, train_x, train_y):
        self.train_x = train_x
        self.train_y = train_y
        self.transforms = transforms.Compose(
                            [transforms.Resize([224, 224]),
                             transforms.ToTensor(),
                             transforms.Normalize(mean=[0.5, 0.5, 0.5],
                                                  std=[0.5, 0.5, 0.5])])
        self.seq_size = 5
        self.head_num=2
        self.node_num=4
        self.feature_dim = 162
        self.img_path = '/home/shuwen/data/data_preprocessing2/annotations/'
        self.person_tracker_bbox = '../3d_pose2gaze/tracker_record_bbox/'
        self.person_battery_bbox = '../3d_pose2gaze/record_bbox/'
        self.obj_bbox = '/home/shuwen/data/data_preprocessing2/post_neighbor_smooth_newseq/'
        self.cate_path = '/home/shuwen/data/data_preprocessing2/track_cate/'
        self.feature_path = '/home/shuwen/data/data_preprocessing2/feature_single/'

    def __getitem__(self, index):
        p1_event, p2_event, memory, indicator = self.train_x[index]
        # p1_event = np.exp(p1_event)/np.exp(p1_event).sum()
        # p2_event = np.exp(p2_event)/np.exp(p2_event).sum()
        event_input = np.hstack([p1_event, p2_event, memory[1:], indicator[1:]])

        actual_val = self.train_y[index]
        labels_mc = np.argmax(actual_val[:4])
        labels_m21 = np.argmax(actual_val[4:8])
        labels_m12 = np.argmax(actual_val[8:12])
        labels_m1 = np.argmax(actual_val[12:16])
        labels_m2 = np.argmax(actual_val[16:20])

        return event_input, labels_mc, labels_m1, labels_m2, labels_m12, labels_m21

    def __len__(self):
        return len(self.train_x)

def collate_fn_event_mem(batch):
    N = len(batch)

    event_batch = np.zeros((N, 16))
    obj_batch = np.zeros((N, 3, 224, 224))
    hog_batch = np.zeros((N, 162*2))
    mc_label_batch = np.zeros(N)
    m1_label_batch = np.zeros(N)
    m2_label_batch = np.zeros(N)
    m12_label_batch = np.zeros(N)
    m21_label_batch = np.zeros(N)

    for i, (event, mc, m1, m2, m12, m21) in enumerate(batch):
        event_batch[i, ...] = event
        mc_label_batch[i,...] = mc
        m1_label_batch[i, ...] = m1
        m2_label_batch[i, ...] = m2
        m12_label_batch[i, ...] = m12
        m21_label_batch[i, ...] = m21

    event_batch = torch.FloatTensor(event_batch)
    mc_label_batch = torch.LongTensor(mc_label_batch)
    m1_label_batch = torch.LongTensor(m1_label_batch)
    m2_label_batch = torch.LongTensor(m2_label_batch)
    m12_label_batch = torch.LongTensor(m12_label_batch)
    m21_label_batch = torch.LongTensor(m21_label_batch)

    return event_batch, mc_label_batch, m1_label_batch, m2_label_batch, m12_label_batch, m21_label_batch

class mydataset(torch.utils.data.Dataset):
    def __init__(self, train_x, train_y):
        self.train_x = train_x
        self.train_y = train_y
        self.transforms = transforms.Compose(
                            [transforms.Resize([224, 224]),
                             transforms.ToTensor(),
                             transforms.Normalize(mean=[0.5, 0.5, 0.5],
                                                  std=[0.5, 0.5, 0.5])])
        self.seq_size = 5
        self.head_num=2
        self.node_num=4
        self.feature_dim = 162
        self.img_path = '/home/shuwen/data/data_preprocessing2/annotations/'
        self.person_tracker_bbox = '../3d_pose2gaze/tracker_record_bbox/'
        self.person_battery_bbox = '../3d_pose2gaze/record_bbox/'
        self.obj_bbox = '/home/shuwen/data/data_preprocessing2/post_neighbor_smooth_newseq/'
        self.cate_path = '/home/shuwen/data/data_preprocessing2/track_cate/'
        self.feature_path = '/home/shuwen/data/data_preprocessing2/feature_single/'

    def __getitem__(self, index):
        p1_event, p2_event, memory, indicator, hog, obj_patch = self.train_x[index]
        p1_event = np.exp(p1_event)/np.exp(p1_event).sum()
        p2_event = np.exp(p2_event)/np.exp(p2_event).sum()
        event_input = np.hstack([p1_event, p2_event, memory[1:], indicator[1:]])
        obj_patch = transforms.ToPILImage()(obj_patch)
        obj_patch = self.transforms(obj_patch)

        actual_val = self.train_y[index]
        labels_mc = np.argmax(actual_val[:4])
        labels_m21 = np.argmax(actual_val[4:8])
        labels_m12 = np.argmax(actual_val[8:12])
        labels_m1 = np.argmax(actual_val[12:16])
        labels_m2 = np.argmax(actual_val[16:20])

        return event_input, obj_patch, hog, labels_mc, labels_m1, labels_m2, labels_m12, labels_m21

    def __len__(self):
        return len(self.train_x)

def collate_fn(batch):
    N = len(batch)

    event_batch = np.zeros((N, 16))
    obj_batch = np.zeros((N, 3, 224, 224))
    hog_batch = np.zeros((N, 162*2))
    mc_label_batch = np.zeros(N)
    m1_label_batch = np.zeros(N)
    m2_label_batch = np.zeros(N)
    m12_label_batch = np.zeros(N)
    m21_label_batch = np.zeros(N)

    for i, (event, obj, hog, mc, m1, m2, m12, m21) in enumerate(batch):
        event_batch[i, ...] = event
        obj_batch[i, ...] = obj
        hog_batch[i, ...] = hog
        mc_label_batch[i,...] = mc
        m1_label_batch[i, ...] = m1
        m2_label_batch[i, ...] = m2
        m12_label_batch[i, ...] = m12
        m21_label_batch[i, ...] = m21

    event_batch = torch.FloatTensor(event_batch)
    obj_batch = torch.FloatTensor(obj_batch)
    hog_batch = torch.FloatTensor(hog_batch)
    mc_label_batch = torch.LongTensor(mc_label_batch)
    m1_label_batch = torch.LongTensor(m1_label_batch)
    m2_label_batch = torch.LongTensor(m2_label_batch)
    m12_label_batch = torch.LongTensor(m12_label_batch)
    m21_label_batch = torch.LongTensor(m21_label_batch)

    return event_batch, obj_batch, hog_batch, mc_label_batch, m1_label_batch, m2_label_batch, m12_label_batch, m21_label_batch

class mydataset_lstm(torch.utils.data.Dataset):
    def __init__(self, train_x, train_y):
        self.train_x = train_x
        self.train_y = train_y
        self.transforms = transforms.Compose(
                            [transforms.Resize([224, 224]),
                             transforms.ToTensor(),
                             transforms.Normalize(mean=[0.5, 0.5, 0.5],
                                                  std=[0.5, 0.5, 0.5])])
        self.seq_size = 5
        self.head_num=2
        self.node_num=4
        self.feature_dim = 162
        self.img_path = '/home/shuwen/data/data_preprocessing2/annotations/'
        self.person_tracker_bbox = '../3d_pose2gaze/tracker_record_bbox/'
        self.person_battery_bbox = '../3d_pose2gaze/record_bbox/'
        self.obj_bbox = '/home/shuwen/data/data_preprocessing2/post_neighbor_smooth_newseq/'
        self.cate_path = '/home/shuwen/data/data_preprocessing2/track_cate/'
        self.feature_path = '/home/shuwen/data/data_preprocessing2/feature_single/'

    def __getitem__(self, index):
        event_input, hog_input, img_input, box_input = self.train_x[index]
        obj_patch_input = np.zeros((self.seq_size, 3, 224, 224))


        for i in range(len(img_input)):

            # obj_patch
            img = cv2.imread(img_input[i])
            x_min, y_min, x_max, y_max = box_input[i]

            obj_patch = img[y_min:y_max, x_min:x_max]
            obj_patch = transforms.ToPILImage()(obj_patch)
            obj_patch = self.transforms(obj_patch).numpy()
            obj_patch_input[i, ...] = obj_patch

        actual_val = self.train_y[index]
        labels_mc = np.argmax(actual_val[:4])
        labels_m21 = np.argmax(actual_val[4:8])
        labels_m12 = np.argmax(actual_val[8:12])
        labels_m1 = np.argmax(actual_val[12:16])
        labels_m2 = np.argmax(actual_val[16:20])

        return event_input, obj_patch_input, hog_input, labels_mc, labels_m1, labels_m2, labels_m12, labels_m21

    def __len__(self):
        return len(self.train_x)

def collate_fn_lstm(batch):
    N = len(batch)
    seq_len = 5

    event_batch = np.zeros((N, seq_len, 16))
    obj_batch = np.zeros((N, seq_len, 3, 224, 224))
    hog_batch = np.zeros((N, seq_len, 162*2))
    mc_label_batch = np.zeros(N)
    m1_label_batch = np.zeros(N)
    m2_label_batch = np.zeros(N)
    m12_label_batch = np.zeros(N)
    m21_label_batch = np.zeros(N)

    for i, (event, obj, hog, mc, m1, m2, m12, m21) in enumerate(batch):
        event_batch[i, ...] = event
        obj_batch[i, ...] = obj
        hog_batch[i, ...] = hog
        mc_label_batch[i,...] = mc
        m1_label_batch[i, ...] = m1
        m2_label_batch[i, ...] = m2
        m12_label_batch[i, ...] = m12
        m21_label_batch[i, ...] = m21

    event_batch = torch.FloatTensor(event_batch)
    obj_batch = torch.FloatTensor(obj_batch)
    hog_batch = torch.FloatTensor(hog_batch)
    mc_label_batch = torch.LongTensor(mc_label_batch)
    m1_label_batch = torch.LongTensor(m1_label_batch)
    m2_label_batch = torch.LongTensor(m2_label_batch)
    m12_label_batch = torch.LongTensor(m12_label_batch)
    m21_label_batch = torch.LongTensor(m21_label_batch)
    return event_batch, obj_batch, hog_batch, mc_label_batch, m1_label_batch, m2_label_batch, m12_label_batch, m21_label_batch

class mydataset_lstm_cnn(torch.utils.data.Dataset):
    def __init__(self, train_x, train_y):
        self.train_x = train_x
        self.train_y = train_y
        self.transforms = transforms.Compose(
                            [transforms.Resize([224, 224]),
                             transforms.ToTensor(),
                             transforms.Normalize(mean=[0.5, 0.5, 0.5],
                                                  std=[0.5, 0.5, 0.5])])
        self.seq_size = 5
        self.head_num=2
        self.node_num=4
        self.feature_dim = 162
        self.img_path = '/home/shuwen/data/data_preprocessing2/annotations/'
        self.person_tracker_bbox = '../3d_pose2gaze/tracker_record_bbox/'
        self.person_battery_bbox = '../3d_pose2gaze/record_bbox/'
        self.obj_bbox = '/home/shuwen/data/data_preprocessing2/post_neighbor_smooth_newseq/'
        self.cate_path = '/home/shuwen/data/data_preprocessing2/track_cate/'
        self.feature_path = '/home/shuwen/data/data_preprocessing2/feature_single/'

    def __getitem__(self, index):
        event_input, hog_input, img_input, box_input = self.train_x[index]
        obj_patch_input = np.zeros((self.seq_size, 3, 224, 224))


        for i in range(len(img_input)):

            # obj_patch
            img = cv2.imread(img_input[i])
            obj_patch = transforms.ToPILImage()(img)
            obj_patch = self.transforms(obj_patch).numpy()
            obj_patch_input[i, ...] = obj_patch

        actual_val = self.train_y[index]
        labels_mc = np.argmax(actual_val[:4])
        labels_m21 = np.argmax(actual_val[4:8])
        labels_m12 = np.argmax(actual_val[8:12])
        labels_m1 = np.argmax(actual_val[12:16])
        labels_m2 = np.argmax(actual_val[16:20])

        return obj_patch_input, hog_input, labels_mc, labels_m1, labels_m2, labels_m12, labels_m21

    def __len__(self):
        return len(self.train_x)

def collate_fn_lstm_cnn(batch):
    N = len(batch)
    seq_len = 5

    obj_batch = np.zeros((N, seq_len, 3, 224, 224))
    hog_batch = np.zeros((N, seq_len, 162*2))
    mc_label_batch = np.zeros(N)
    m1_label_batch = np.zeros(N)
    m2_label_batch = np.zeros(N)
    m12_label_batch = np.zeros(N)
    m21_label_batch = np.zeros(N)

    for i, (obj, hog, mc, m1, m2, m12, m21) in enumerate(batch):
        obj_batch[i, ...] = obj
        hog_batch[i, ...] = hog
        mc_label_batch[i,...] = mc
        m1_label_batch[i, ...] = m1
        m2_label_batch[i, ...] = m2
        m12_label_batch[i, ...] = m12
        m21_label_batch[i, ...] = m21

    obj_batch = torch.FloatTensor(obj_batch)
    hog_batch = torch.FloatTensor(hog_batch)
    mc_label_batch = torch.LongTensor(mc_label_batch)
    m1_label_batch = torch.LongTensor(m1_label_batch)
    m2_label_batch = torch.LongTensor(m2_label_batch)
    m12_label_batch = torch.LongTensor(m12_label_batch)
    m21_label_batch = torch.LongTensor(m21_label_batch)
    return obj_batch, hog_batch, mc_label_batch, m1_label_batch, m2_label_batch, m12_label_batch, m21_label_batch

class mydataset_cnn(torch.utils.data.Dataset):
    def __init__(self, train_x, train_y):
        self.train_x = train_x
        self.train_y = train_y
        self.transforms = transforms.Compose(
                            [transforms.Resize([224, 224]),
                             transforms.ToTensor(),
                             transforms.Normalize(mean=[0.5, 0.5, 0.5],
                                                  std=[0.5, 0.5, 0.5])])
        self.seq_size = 5
        self.head_num=2
        self.node_num=4
        self.feature_dim = 162
        self.img_path = '/home/shuwen/data/data_preprocessing2/annotations/'
        self.person_tracker_bbox = '../3d_pose2gaze/tracker_record_bbox/'
        self.person_battery_bbox = '../3d_pose2gaze/record_bbox/'
        self.obj_bbox = '/home/shuwen/data/data_preprocessing2/post_neighbor_smooth_newseq/'
        self.cate_path = '/home/shuwen/data/data_preprocessing2/track_cate/'
        self.feature_path = '/home/shuwen/data/data_preprocessing2/feature_single/'

    def __getitem__(self, index):
        img_input, hog_input = self.train_x[index]
        obj_patch_input = np.zeros((3, 224, 224))

        img = cv2.imread(img_input)

        obj_patch = transforms.ToPILImage()(img)
        obj_patch = self.transforms(obj_patch).numpy()
        obj_patch_input = obj_patch

        actual_val = self.train_y[index]
        labels_mc = np.argmax(actual_val[:4])
        labels_m21 = np.argmax(actual_val[4:8])
        labels_m12 = np.argmax(actual_val[8:12])
        labels_m1 = np.argmax(actual_val[12:16])
        labels_m2 = np.argmax(actual_val[16:20])

        return obj_patch_input, hog_input, labels_mc, labels_m1, labels_m2, labels_m12, labels_m21

    def __len__(self):
        return len(self.train_x)

def collate_fn_cnn(batch):
    N = len(batch)

    obj_batch = np.zeros((N, 3, 224, 224))
    hog_batch = np.zeros((N, 162*2))
    mc_label_batch = np.zeros(N)
    m1_label_batch = np.zeros(N)
    m2_label_batch = np.zeros(N)
    m12_label_batch = np.zeros(N)
    m21_label_batch = np.zeros(N)

    for i, (obj, hog, mc, m1, m2, m12, m21) in enumerate(batch):
        obj_batch[i, ...] = obj
        hog_batch[i, ...] = hog
        mc_label_batch[i,...] = mc
        m1_label_batch[i, ...] = m1
        m2_label_batch[i, ...] = m2
        m12_label_batch[i, ...] = m12
        m21_label_batch[i, ...] = m21

    obj_batch = torch.FloatTensor(obj_batch)
    hog_batch = torch.FloatTensor(hog_batch)
    mc_label_batch = torch.LongTensor(mc_label_batch)
    m1_label_batch = torch.LongTensor(m1_label_batch)
    m2_label_batch = torch.LongTensor(m2_label_batch)
    m12_label_batch = torch.LongTensor(m12_label_batch)
    m21_label_batch = torch.LongTensor(m21_label_batch)
    return obj_batch, hog_batch, mc_label_batch, m1_label_batch, m2_label_batch, m12_label_batch, m21_label_batch

class mydataset_raw_feature(torch.utils.data.Dataset):
    def __init__(self, train_x, train_y):
        self.train_x = train_x
        self.train_y = train_y
        self.transforms = transforms.Compose(
                            [transforms.Resize([224, 224]),
                             transforms.ToTensor(),
                             transforms.Normalize(mean=[0.5, 0.5, 0.5],
                                                  std=[0.5, 0.5, 0.5])])
        self.seq_size = 5
        self.head_num=2
        self.node_num=4
        self.feature_dim = 162
        self.img_path = '/home/shuwen/data/data_preprocessing2/annotations/'
        self.person_tracker_bbox = '../3d_pose2gaze/tracker_record_bbox/'
        self.person_battery_bbox = '../3d_pose2gaze/record_bbox/'
        self.obj_bbox = '/home/shuwen/data/data_preprocessing2/post_neighbor_smooth_newseq/'
        self.cate_path = '/home/shuwen/data/data_preprocessing2/track_cate/'
        self.feature_path = '/home/shuwen/data/data_preprocessing2/feature_single/'

    def __getitem__(self, index):
        input = self.train_x[index]

        actual_val = self.train_y[index]
        labels_mc = np.argmax(actual_val[:4])
        labels_m21 = np.argmax(actual_val[4:8])
        labels_m12 = np.argmax(actual_val[8:12])
        labels_m1 = np.argmax(actual_val[12:16])
        labels_m2 = np.argmax(actual_val[16:20])

        return input, labels_mc, labels_m1, labels_m2, labels_m12, labels_m21

    def __len__(self):
        return len(self.train_x)

def collate_fn_raw_feature(batch):
    N = len(batch)

    event_batch = np.zeros((N, 16))
    obj_batch = np.zeros((N, 3, 224, 224))
    hog_batch = np.zeros((N, 162*2))
    mc_label_batch = np.zeros(N)
    m1_label_batch = np.zeros(N)
    m2_label_batch = np.zeros(N)
    m12_label_batch = np.zeros(N)
    m21_label_batch = np.zeros(N)

    for i, (input, mc, m1, m2, m12, m21) in enumerate(batch):
        event_batch[i, ...] = input
        mc_label_batch[i,...] = mc
        m1_label_batch[i, ...] = m1
        m2_label_batch[i, ...] = m2
        m12_label_batch[i, ...] = m12
        m21_label_batch[i, ...] = m21

    event_batch = torch.FloatTensor(event_batch)
    mc_label_batch = torch.LongTensor(mc_label_batch)
    m1_label_batch = torch.LongTensor(m1_label_batch)
    m2_label_batch = torch.LongTensor(m2_label_batch)
    m12_label_batch = torch.LongTensor(m12_label_batch)
    m21_label_batch = torch.LongTensor(m21_label_batch)

    return event_batch, mc_label_batch, m1_label_batch, m2_label_batch, m12_label_batch, m21_label_batch

def main():

    # data_path = '/home/shuwen/data/data_preprocessing2/mind_training_add_hog/'
    data_path = '/home/shuwen/data/data_preprocessing2/mind_training_event_memory/'
    model_type = 'event_memory'

    # calculate_dis(data_path, model_type)
    # train_x, train_y, validate_x, validate_y, test_x, test_y = get_data(data_path, model_type)
    # print(len(train_x), len(validate_x), len(test_x))

    learningRate = 0.01
    epochs = 300
    batch_size = 256
    #
    # train(model_type, learningRate, epochs, batch_size, train_x, train_y, validate_x, validate_y) #, checkpoint='./cptk_single/model_best.pth')
    # net = MLP_Event_Memory()
    # net.load_state_dict(torch.load('./cptk_event_memory/model_best.pth'))
    # if torch.cuda.is_available():
    #     net.cuda()
    # net.eval()
    # test_score(net, test_x, test_y, batch_size, model_type, 'test')

    test_data_seq_tree_search('tree_search')
    # test_data_seq_tree_search('tree_search_frame')
    # test_data_seq_tree_search('tree_search_init')
    # test_data_seq_tree_search('tree_search_unif_event')
    # test_data_seq_tree_search('tree_search_event_likelihood')
    # test_data_seq('event_memory')


def test_score(net, data, label, batch_size, proj_name = None, dataset = None):

    net.eval()
    total_mc = np.empty(0)
    total_m21 = np.empty(0)
    total_m12 = np.empty(0)
    total_m2 = np.empty(0)
    total_m1 = np.empty(0)

    total_act_mc = np.empty(0)
    total_act_m21 = np.empty(0)
    total_act_m12 = np.empty(0)
    total_act_m2 = np.empty(0)
    total_act_m1 = np.empty(0)

    if proj_name == 'single' or proj_name == 'single_one_hot' or proj_name == 'tree_search':
        train_set = mydataset(data, label)
        train_loader = torch.utils.data.DataLoader(train_set, collate_fn=collate_fn, batch_size=batch_size,
                                                   shuffle=False)
    elif proj_name == 'cnn' or proj_name == 'cnn_no_hog':
        train_set = mydataset_cnn(data, label)
        train_loader = torch.utils.data.DataLoader(train_set, collate_fn=collate_fn_cnn, batch_size=batch_size,
                                                   shuffle=False)
    elif proj_name == 'event_memory':
        train_set = mydataset_event_mem(data, label)
        train_loader = torch.utils.data.DataLoader(train_set, collate_fn=collate_fn_event_mem, batch_size=batch_size,
                                                   shuffle=False)
    else:
        train_set = mydataset_lstm(data, label)
        train_loader = torch.utils.data.DataLoader(train_set, collate_fn=collate_fn_lstm, batch_size=batch_size,
                                                   shuffle=False)


    net.eval()

    pbar = tqdm(train_loader)
    for batch in pbar:
        event_batch, mc_label_batch, m1_label_batch, m2_label_batch, m12_label_batch, m21_label_batch = batch
        # obj_batch, hog_batch, mc_label_batch, m1_label_batch, m2_label_batch, m12_label_batch, m21_label_batch = batch
        event_batch = event_batch.cuda()
        # obj_batch = obj_batch.cuda()
        # hog_batch = hog_batch.cuda()
        mc_label_batch = mc_label_batch.numpy()
        m1_label_batch = m1_label_batch.numpy()
        m2_label_batch = m2_label_batch.numpy()
        m12_label_batch = m12_label_batch.numpy()
        m21_label_batch = m21_label_batch.numpy()


        m1, m2, m12, m21, mc = net(event_batch)
        # m1, m2, m12, m21, mc = net(obj_batch)

        max_score, idx_mc = torch.max(mc, 1)
        max_score, idx_m21 = torch.max(m21, 1)
        max_score, idx_m12 = torch.max(m12, 1)
        max_score, idx_m1 = torch.max(m1, 1)
        max_score, idx_m2 = torch.max(m2, 1)
        # max_score, idx_mg = torch.max(mg, 1)
        total_mc = np.append(total_mc, idx_mc.cpu().numpy())
        total_m21 = np.append(total_m21, idx_m21.cpu().numpy())
        total_m12 = np.append(total_m12, idx_m12.cpu().numpy())
        total_m1 = np.append(total_m1, idx_m1.cpu().numpy())
        total_m2 = np.append(total_m2, idx_m2.cpu().numpy())
        # total_mg = np.append(total_mg, idx_mg.cpu().numpy())

        total_act_mc = np.append(total_act_mc, mc_label_batch)
        total_act_m21 = np.append(total_act_m21, m21_label_batch)
        total_act_m12 = np.append(total_act_m12, m12_label_batch)
        total_act_m1 = np.append(total_act_m1, m1_label_batch)
        total_act_m2 = np.append(total_act_m2, m2_label_batch)



    if dataset:
        results_mc = metrics.classification_report(total_act_mc, total_mc, digits=3)
        results_m1 = metrics.classification_report(total_act_m1, total_m1, digits=3)
        results_m2 = metrics.classification_report(total_act_m2, total_m2, digits=3)
        results_m12 = metrics.classification_report(total_act_m12, total_m12, digits=3)
        results_m21 = metrics.classification_report(total_act_m21, total_m21, digits=3)

        print(results_mc)
        print(results_m1)
        print(results_m2)
        print(results_m12)
        print(results_m21)

        cmc = metrics.confusion_matrix(total_act_mc, total_mc)
        cm1 = metrics.confusion_matrix(total_act_m1, total_m1)
        cm2 = metrics.confusion_matrix(total_act_m2, total_m2)
        cm12 = metrics.confusion_matrix(total_act_m12, total_m12)
        cm21 = metrics.confusion_matrix(total_act_m21, total_m21)

        plot_confusion_matrix(cmc)
        plot_confusion_matrix(cm1)
        plot_confusion_matrix(cm2)
        plot_confusion_matrix(cm12)
        plot_confusion_matrix(cm21)

        score1 = metrics.accuracy_score(total_act_mc, total_mc)
        score2 = metrics.accuracy_score(total_act_m1, total_m1)
        score3 = metrics.accuracy_score(total_act_m2, total_m2)
        score4 = metrics.accuracy_score(total_act_m12, total_m12)
        score5 = metrics.accuracy_score(total_act_m21, total_m21)
        print([score1, score2, score3, score4, score5])
        with open('./cptk_' + proj_name + '/' + dataset + '.p', 'wb') as f:
            pickle.dump([results_m1, results_m2, results_m12, results_m21, results_mc], f)

    score1 = metrics.accuracy_score(total_act_mc, total_mc)
    score2 = metrics.accuracy_score(total_act_m1, total_m1)
    score3 = metrics.accuracy_score(total_act_m2, total_m2)
    score4 = metrics.accuracy_score(total_act_m12, total_m12)
    score5 = metrics.accuracy_score(total_act_m21, total_m21)
    return [score1, score2, score3, score4, score5]


def train(save_prefix, learningRate, epochs, batch_size, train_x, train_y, validate_x, validate_y, checkpoint = None, startepoch = None):
    if save_prefix == 'single' or save_prefix == 'tree_search':
        model = MindHog()
    elif save_prefix == 'single_one_hot':
        model = MindHog()
    elif save_prefix == 'cnn':
        model = MindCNN()
    elif save_prefix == 'cnn_no_hog':
        model = MindCNNNoHog()
    elif save_prefix == 'event_memory':
        model = MLP_Event_Memory()
    else:
        model = MindLSTMHog()

    if checkpoint is not None:
        model.load_state_dict(torch.load(checkpoint))
    if startepoch is not None:
        startepoch = startepoch
    else:
        startepoch = 0
    ##### For GPU #######
    if torch.cuda.is_available():
        model.cuda()
    # weights = [1/39., 1/3., 1/391., 1/3702.]
    # weights = torch.FloatTensor(weights).cuda()
    # criterionc = torch.nn.CrossEntropyLoss(weight=weights)
    # weights = [1/87., 1/11., 1/929., 1/3108.]
    # weights = torch.FloatTensor(weights).cuda()
    # criterionm12 = torch.nn.CrossEntropyLoss(weight=weights)
    # weights = [1/78., 1/11., 1/847., 1/3199.]
    # weights = torch.FloatTensor(weights).cuda()
    # criterionm21 = torch.nn.CrossEntropyLoss(weight=weights)
    # weights = [1/175., 1/6., 1/391., 1/3702.]
    # weights = torch.FloatTensor(weights).cuda()
    # criterionm1 = torch.nn.CrossEntropyLoss(weight=weights)
    # weights = [1/177., 1/5., 1/2599., 1/1354.]
    # weights = torch.FloatTensor(weights).cuda()
    # criterionm2 = torch.nn.CrossEntropyLoss(weight=weights)
    # criterionmg = torch.nn.CrossEntropyLoss()

    criterionc = torch.nn.CrossEntropyLoss()
    criterionm12 = torch.nn.CrossEntropyLoss()
    criterionm21 = torch.nn.CrossEntropyLoss()
    criterionm1 = torch.nn.CrossEntropyLoss()
    criterionm2 = torch.nn.CrossEntropyLoss()
    # criterionmg = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learningRate)
    # scheduler = MultiStepLR(optimizer, milestones=[500, 1000, 1500], gamma=0.1)
    losses_m1, losses_m2, losses_m12, losses_m21, losses_mc = [], [], [], [], []
    best_score = 0

    if save_prefix == 'single' or save_prefix == 'single_one_hot' or save_prefix == 'tree_search':
        train_set = mydataset(train_x, train_y)
        train_loader = torch.utils.data.DataLoader(train_set, collate_fn=collate_fn, batch_size=batch_size,
                                                   shuffle=False)
    elif save_prefix == 'cnn' or save_prefix == 'cnn_no_hog':
        train_set = mydataset_cnn(train_x, train_y)
        train_loader = torch.utils.data.DataLoader(train_set, collate_fn=collate_fn_cnn, batch_size=batch_size,
                                                   shuffle=False)
    elif save_prefix == 'event_memory':
        train_set = mydataset_event_mem(train_x, train_y)
        train_loader = torch.utils.data.DataLoader(train_set, collate_fn=collate_fn_event_mem, batch_size=batch_size,
                                                   shuffle=False)
    else:
        train_set = mydataset_lstm(train_x, train_y)
        train_loader = torch.utils.data.DataLoader(train_set, collate_fn=collate_fn_lstm, batch_size=batch_size,
                                                   shuffle=False)

    for epoch in range(startepoch, epochs):
        model.train()
        # training set -- perform model training
        epoch_training_loss_m1, epoch_training_loss_m2, epoch_training_loss_m12, epoch_training_loss_m21, epoch_training_loss_mc\
            = 0.0, 0.0, 0.0, 0.0, 0.0
        num_batches = 0
        pbar = tqdm(train_loader)
        for batch in pbar:
            if save_prefix == 'cnn' or save_prefix == 'cnn_no_hog':
                obj_batch, hog_batch, mc_label_batch, m1_label_batch, m2_label_batch, m12_label_batch, m21_label_batch = batch
            elif save_prefix == 'event_memory':
                event_batch, mc_label_batch, m1_label_batch, m2_label_batch, m12_label_batch, m21_label_batch = batch
            else:
                event_batch, obj_batch, hog_batch, mc_label_batch, m1_label_batch, m2_label_batch, m12_label_batch, m21_label_batch = batch
            event_batch = event_batch.cuda()
            # obj_batch = obj_batch.cuda()
            # hog_batch = hog_batch.cuda()
            mc_label_batch = mc_label_batch.cuda()
            m1_label_batch = m1_label_batch.cuda()
            m2_label_batch = m2_label_batch.cuda()
            m12_label_batch = m12_label_batch.cuda()
            m21_label_batch = m21_label_batch.cuda()

            # Make gradients zero for parameters 'W', 'b'
            optimizer.zero_grad()

            # m1, m2, m12, m21, mc = model(obj_batch)
            m1, m2, m12, m21, mc = model(event_batch)
            loss_m1, loss_m2, loss_m12, loss_m21, loss_mc = criterionm1(m1, m1_label_batch), criterionm2(m2, m2_label_batch), \
            criterionm12(m12, m12_label_batch), criterionm21(m21, m21_label_batch), criterionc(mc, mc_label_batch)
            loss = loss_m1 + loss_m2 + 1.5*loss_m12 + loss_m21 + loss_mc
            loss.backward()

            optimizer.step()

            # calculating loss
            epoch_training_loss_m1 += loss_m1.data.item()
            epoch_training_loss_m2 += loss_m2.data.item()
            epoch_training_loss_m12 += loss_m12.data.item()
            epoch_training_loss_m21 += loss_m21.data.item()
            epoch_training_loss_mc += loss_mc.data.item()
            num_batches += 1

        # scheduler.step()
        print("epoch:{}/m1_loss:{}, m2_loss:{}, m12_loss:{}, m21_loss:{}, mc_loss:{}".format(
            epoch, epoch_training_loss_m1/num_batches, epoch_training_loss_m2/num_batches, epoch_training_loss_m12/num_batches,
            epoch_training_loss_m21 / num_batches, epoch_training_loss_mc/num_batches))
        losses_m1.append(epoch_training_loss_m1/num_batches)
        losses_m2.append(epoch_training_loss_m2 / num_batches)
        losses_m12.append(epoch_training_loss_m12 / num_batches)
        losses_m21.append(epoch_training_loss_m21 / num_batches)
        losses_mc.append(epoch_training_loss_mc / num_batches)

        score = test_score(model, validate_x, validate_y, batch_size, save_prefix)
        if sum(score) > best_score:
            best_score = sum(score)
            print('best_score: mc:{}, m1:{}, m2:{}, m12:{}, m21:{}'.format(score[0], score[1], score[2], score[3], score[4]))
            save_path = './cptk_' + save_prefix + '/model_best.pth'
            torch.save(model.state_dict(), save_path)
        if epoch%100 == 0:
            for param in optimizer.param_groups:
                if param['lr'] > 1e-5:
                    param['lr'] = param['lr']*0.5

        if epoch%50 == 0:
            save_path = './cptk_' + save_prefix + '/model_' +str(epoch)+'.pth'
            torch.save(model.state_dict(), save_path)
            legend_labels = ['m1', 'm2', 'm12', 'm21', 'mc']
            plt.plot(losses_m1)
            plt.plot(losses_m2)
            plt.plot(losses_m12)
            plt.plot(losses_m21)
            plt.plot(losses_mc)
            plt.legend(legend_labels)
            plt.show()

def check_overlap_return_area(head_box, obj_curr):
    max_left = max(head_box[0], obj_curr[0])
    max_top = max(head_box[1], obj_curr[1])
    min_right = min(head_box[2], obj_curr[2])
    min_bottom = min(head_box[3], obj_curr[3])
    if (min_right - max_left) > 0 and (min_bottom - max_top) > 0:
        return (min_right - max_left)*(min_bottom - max_top)
    return -100

def get_obj_name(obj_bbox, annt, frame_id):
    obj_candidates = annt.loc[annt.frame == frame_id]
    max_overlap = 0
    max_name = None
    max_bbox = None
    obj_bbox = [obj_bbox[0], obj_bbox[1], obj_bbox[0] + obj_bbox[2], obj_bbox[1] + obj_bbox[3]]
    obj_area = (obj_bbox[2] - obj_bbox[0])*(obj_bbox[3] - obj_bbox[1])
    for index, obj_candidate in obj_candidates.iterrows():
        if obj_candidate['name'].startswith('P'):
            continue
        candidate_bbox = [obj_candidate['x_min'], obj_candidate['y_min'], obj_candidate['x_max'], obj_candidate['y_max']]
        overlap = check_overlap_return_area(obj_bbox, candidate_bbox)
        if overlap > max_overlap and overlap/obj_area < 1.2 and overlap/obj_area > 0.8:
            max_overlap = overlap
            max_name = obj_candidate['name']
            max_bbox = candidate_bbox
    if max_overlap > 0:
        return max_name, max_bbox
    return None, None

def update_memory(memory, mind_name, fluent, loc):
    if fluent == 0 or fluent == 2:
        memory[mind_name]['loc'] = loc
    elif fluent == 1:
        memory[mind_name]['loc'] = None

    return memory

def get_grid_location_using_bbox(obj_frame):
    x_min = obj_frame[0]
    y_min = obj_frame[1]
    x_max = obj_frame[0] + obj_frame[2]
    y_max = obj_frame[1] + obj_frame[3]
    gridLW = 1280 / 25.
    gridLH = 720 / 15.
    center_x, center_y = (x_min + x_max)/2, (y_min + y_max)/2
    X, Y = int(center_x / gridLW), int(center_y / gridLH)
    return X, Y

def test_data_seq(prj_name):
    if prj_name == 'gru':
        net = MindGRU()
        net.load_state_dict(torch.load('./cptk_gru/model_350.pth'))
        seq_len = 5
    elif prj_name == 'single':
        net = MindHog()
        net.load_state_dict(torch.load('./cptk_single/model_best.pth'))
        seq_len = 1
    elif prj_name == 'lstm_sep':
        net = MindLSTMHog()
        net.load_state_dict(torch.load('./cptk_lstm_sep/model_best.pth'))
        seq_len = 5
    elif prj_name == 'event_memory':
        net = MLP_Event_Memory()
        net.load_state_dict(torch.load('./cptk_event_memory/model_best.pth'))
        seq_len = 1
    else:
        net = MindLSTMSep()
        net.load_state_dict(torch.load('./cptk_lstm_sep/model_best.pth'))
        seq_len = 5
    if torch.cuda.is_available():
        net.cuda()
    net.eval()
    event_label_path = '/home/shuwen/data/data_preprocessing2/event_classfied_label/'
    reannotation_path = '/home/shuwen/data/data_preprocessing2/regenerate_annotation/'
    annotation_path = '/home/shuwen/data/data_preprocessing2/reformat_annotation/'
    color_img_path = '/home/shuwen/data/data_preprocessing2/annotations/'
    feature_path = '/home/shuwen/data/data_preprocessing2/feature_single/'
    save_path = '/home/shuwen/data/data_preprocessing2/mind_output/'
    event_tree_path = './BestTree_ours_0531_all_clips/'

    with open('person_id.p', 'rb') as f:
        person_ids = pickle.load(f)
    obj_transforms = transforms.Compose(
        [transforms.Resize([224, 224]),
         transforms.ToTensor(),
         transforms.Normalize(mean=[0.5, 0.5, 0.5],
                              std=[0.5, 0.5, 0.5])])
    clips = os.listdir(event_label_path)
    m1_predict, m1_real = [], []
    m2_predict, m2_real = [], []
    m12_predict, m12_real = [], []
    m21_predict, m21_real = [], []
    mc_predict, mc_real = [], []
    mg_predict, mg_real = [], []
    for clip in mind_test_clips:
        if not os.path.exists(reannotation_path + clip):
            continue
        print(clip)
        with open(reannotation_path + clip, 'rb') as f:
            obj_records = pickle.load(f)
        with open(event_label_path + clip, 'rb') as f:
            event_segs = pickle.load(f)
        with open(feature_path + clip, 'rb') as f:
            features = pickle.load(f)
        with open(event_tree_path + clip, 'rb') as f:
            event_tree = pickle.load(f)
        img_names = sorted(glob.glob(color_img_path + clip.split('.')[0] + '/kinect/*.jpg'))
        battery_events_by_frame, tracker_events_by_frame = reformat_events_tree_search(event_tree, len(img_names))
        # battery_events_by_frame, tracker_events_by_frame = reformat_events(event_segs, len(img_names))
        if person_ids[clip.split('.')[0]] == 'P1':
            p1_events_by_frame = tracker_events_by_frame
            p2_events_by_frame = battery_events_by_frame
            p1_hog = features[1]
            p2_hog = features[2]
        else:
            p1_events_by_frame = battery_events_by_frame
            p2_events_by_frame = tracker_events_by_frame
            p1_hog = features[2]
            p2_hog = features[1]
        annt = pd.read_csv(annotation_path + clip.split('.')[0] + '.txt', sep=",", header=None)
        annt.columns = ["obj_id", "x_min", "y_min", "x_max", "y_max", "frame", "lost", "occluded", "generated", "name",
                        "label"]
        obj_names = annt.name.unique()
        img_names = sorted(glob.glob(color_img_path + clip.split('.')[0] + '/kinect/*.jpg'))
        for obj_name in obj_names:
            if obj_name.startswith('P'):
                continue
            print(obj_name)
            memory = {'mg':{'fluent':None, 'loc':None}, 'mc':{'fluent':None, 'loc':None}, 'm21':{'fluent':None, 'loc':None},
                      'm12': {'fluent': None, 'loc': None}, 'm1':{'fluent':None, 'loc':None}, 'm2':{'fluent':None, 'loc':None}}
            for frame_id in range(p1_events_by_frame.shape[0]):
                # flag = 0
                # for i in range(-(seq_len - 1), 1, 1):
                #     curr_frame_id = max(frame_id + i, 0)
                #     p1_event = p1_events_by_frame[curr_frame_id]
                #     p2_event = p2_events_by_frame[curr_frame_id]
                #
                #     if np.all(p1_event == np.array([0, 0, 0])) or np.all(p2_event == np.array([0, 0, 0])):
                #         flag = 1
                # if flag:
                #     m1_predict.append(3)
                #     m2_predict.append(3)
                #     m12_predict.append(3)
                #     m21_predict.append(3)
                #     mc_predict.append(3)
                #     curr_df = annt.loc[(annt.frame == frame_id) & (annt.name == obj_name)]
                #     curr_loc = get_grid_location(curr_df)
                #     memory = update_memory(memory, 'm1', 3, curr_loc)
                #     memory = update_memory(memory, 'm2', 3, curr_loc)
                #     memory = update_memory(memory, 'm12', 3, curr_loc)
                #     memory = update_memory(memory, 'm21', 3, curr_loc)
                #     memory = update_memory(memory, 'mc', 3, curr_loc)
                #     memory = update_memory(memory, 'mg', 2, curr_loc)
                #     obj_record = obj_records[obj_name][frame_id]
                #     for mind_name in obj_record:
                #         if mind_name == 'm1':
                #             m1_real.append(obj_record[mind_name]['fluent'])
                #         elif mind_name == 'm2':
                #             m2_real.append(obj_record[mind_name]['fluent'])
                #         elif mind_name == 'm12':
                #             m12_real.append(obj_record[mind_name]['fluent'])
                #         elif mind_name == 'm21':
                #             m21_real.append(obj_record[mind_name]['fluent'])
                #         elif mind_name == 'mc':
                #             mc_real.append(obj_record[mind_name]['fluent'])
                #         elif mind_name == 'mg':
                #             mg_real.append(obj_record[mind_name]['fluent'])
                #     continue

                event_input = np.zeros((seq_len, 16))
                obj_patch_input = np.zeros((seq_len, 3, 224, 224))
                hog_input = np.zeros((seq_len, 162*2))
                obj_record = obj_records[obj_name][frame_id]

                for mind_name in obj_record:
                    if mind_name == 'm1':
                        m1_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'm2':
                        m2_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'm12':
                        m12_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'm21':
                        m21_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'mc':
                        mc_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'mg':
                        mg_real.append(obj_record[mind_name]['fluent'])

                for i in range(-(seq_len - 1), 1, 1):
                    curr_frame_id = max(frame_id + i, 0)
                    # curr_loc
                    curr_df = annt.loc[(annt.frame == curr_frame_id) & (annt.name == obj_name)]
                    curr_loc = get_grid_location(curr_df)
                    # event
                    p1_event = p1_events_by_frame[curr_frame_id]
                    p2_event = p2_events_by_frame[curr_frame_id]
                    # p1_event = np.exp(p1_event)/np.exp(p1_event).sum()
                    # p2_event = np.exp(p2_event)/np.exp(p2_event).sum()
                    event_input[i + seq_len - 1, :3] = p1_event
                    event_input[i + seq_len - 1, 3:6] = p2_event
                    # memory
                    memory_dist = []
                    indicator = []
                    for mind_name in memory.keys():
                        if mind_name == 'mg':
                            continue
                        if curr_frame_id == 0:
                            memory_dist.append(0)
                            indicator.append(0)
                        else:
                            if frame_id%50 == 0:
                                memory_loc = obj_records[obj_name][curr_frame_id - 1][mind_name]['loc']
                            else:
                                memory_loc = memory[mind_name]['loc']
                            # memory_loc = obj_records[obj_name][curr_frame_id - 1][mind_name]['loc']
                            if memory_loc is not None:
                                curr_loc = np.array(curr_loc)
                                memory_loc = np.array(memory_loc)
                                memory_dist.append(np.linalg.norm(curr_loc - memory_loc))
                                indicator.append(1)
                            else:
                                memory_dist.append(0)
                                indicator.append(0)
                    # get predicted value
                    memory_dist = np.array(memory_dist)
                    indicator = np.array(indicator)
                    event_input[i + seq_len - 1, 6:6 + 5] = memory_dist
                    event_input[i + seq_len - 1, 6+5:] = indicator
                    # hog
                    # hog_tracker = p1_hog[frame_id][-162-10:-10]
                    # hog_battery = p2_hog[frame_id][-162-10:-10]
                    # hog_feature = np.hstack([hog_tracker, hog_battery])
                    # hog_input[i + seq_len - 1, :] = hog_feature
                    # # obj_patch
                    # img = cv2.imread(img_names[frame_id])
                    # obj_frame = annt.loc[(annt.frame == frame_id) & (annt.name == obj_name)]
                    # x_min = obj_frame['x_min'].item()
                    # y_min = obj_frame['y_min'].item()
                    # x_max = obj_frame['x_max'].item()
                    # y_max = obj_frame['y_max'].item()
                    # img_patch = img[y_min:y_max, x_min:x_max]
                    # obj_patch = transforms.ToPILImage()(img_patch)
                    # obj_patch = obj_transforms(obj_patch).numpy()
                    # obj_patch_input[i + seq_len - 1, ...] = obj_patch


                # get input
                event_input = torch.from_numpy(event_input).float().cuda().view((1, -1))
                # hog_input = torch.from_numpy(hog_input).float().cuda().view((1, -1))
                #
                # obj_patch = torch.FloatTensor(obj_patch_input).cuda()
                # obj_patch = obj_patch.view((1, 3, 224, 224))
                m1, m2, m12, m21, mc = net(event_input) #, obj_patch, hog_input)
                max_score, idx_mc = torch.max(mc, 1)
                max_score, idx_m21 = torch.max(m21, 1)
                max_score, idx_m12 = torch.max(m12, 1)
                max_score, idx_m1 = torch.max(m1, 1)
                max_score, idx_m2 = torch.max(m2, 1)
                m1_predict.append(idx_m1.cpu().numpy()[0])
                m2_predict.append(idx_m2.cpu().numpy()[0])
                m12_predict.append(idx_m12.cpu().numpy()[0])
                m21_predict.append(idx_m21.cpu().numpy()[0])
                mc_predict.append(idx_mc.cpu().numpy()[0])
                # update memory
                curr_df = annt.loc[(annt.frame == frame_id) & (annt.name == obj_name)]
                curr_loc = get_grid_location(curr_df)
                memory = update_memory(memory, 'm1', idx_m1, curr_loc)
                memory = update_memory(memory, 'm2', idx_m2, curr_loc)
                memory = update_memory(memory, 'm12', idx_m12, curr_loc)
                memory = update_memory(memory, 'm21', idx_m21, curr_loc)
                memory = update_memory(memory, 'mc', idx_mc, curr_loc)
                memory = update_memory(memory, 'mg', 2, curr_loc)

    # with open('./cptk_' + prj_name + '/' + 'output.p', 'wb') as f:
    #     pickle.dump({'mc':[mc_predict, mc_real], 'm1':[m1_predict, m1_real], 'm2':[m2_predict, m2_real],
    #                 'm12':[m12_predict, m12_real], 'm21':[m21_predict, m21_real]}, f)
    results_mc = metrics.classification_report(mc_real, mc_predict, digits=3)
    results_m1 = metrics.classification_report(m1_real, m1_predict, digits=3)
    results_m2 = metrics.classification_report(m2_real, m2_predict, digits=3)
    results_m12 = metrics.classification_report(m12_real, m12_predict, digits=3)
    results_m21 = metrics.classification_report(m21_real, m21_predict, digits=3)
    print(results_mc)
    print(results_m1)
    print(results_m2)
    print(results_m12)
    print(results_m21)

    cmc = metrics.confusion_matrix(mc_real, mc_predict)
    cm1 = metrics.confusion_matrix(m1_real, m1_predict)
    cm2 = metrics.confusion_matrix(m2_real, m2_predict)
    cm12 = metrics.confusion_matrix(m12_real, m12_predict)
    cm21 = metrics.confusion_matrix(m21_real, m21_predict)
    plot_confusion_matrix(cmc)
    plot_confusion_matrix(cm1)
    plot_confusion_matrix(cm2)
    plot_confusion_matrix(cm12)
    plot_confusion_matrix(cm21)
    score1 = metrics.accuracy_score(mc_real, mc_predict)
    score2 = metrics.accuracy_score(m1_real, m1_predict)
    score3 = metrics.accuracy_score(m2_real, m2_predict)
    score4 = metrics.accuracy_score(m12_real, m12_predict)
    score5 = metrics.accuracy_score(m21_real, m21_predict)
    print([score1, score2, score3, score4, score5])

    with open('./cptk_' + prj_name + '/' + 'seq.p', 'wb') as f:
        pickle.dump([[results_m1, results_m2, results_m12, results_m21, results_mc],
                    [score1, score2, score3, score4, score5],
                     [cmc, cm1, cm2, cm12, cm21]], f)

def change2vec(predict, mc_real):
    predict = np.array(predict)
    mc_real = np.array(mc_real)

    mc_reall = np.zeros((mc_real.size, mc_real.max() + 1))
    mc_reall[np.arange(mc_real.size), mc_real] = 1

    return predict, mc_reall

def test_data_seq_baseline(prj_name):
    if prj_name == 'gru':
        net = MindGRU()
        net.load_state_dict(torch.load('./cptk_gru/model_350.pth'))
        seq_len = 5
    elif prj_name == 'single':
        net = MindHog()
        net.load_state_dict(torch.load('./cptk_single/model_best.pth'))
        seq_len = 1
    elif prj_name == 'cnn':
        net = MindCNN()
        net.load_state_dict(torch.load('./cptk_cnn/model_best.pth'))
        seq_len = 1
    elif prj_name == 'raw_feature':
        net = MLP_Feature()
        net.load_state_dict(torch.load('./cptk_raw_feature/model_best.pth'))
        seq_len = 1
    elif prj_name == 'lstm_cnn':
        net = MindLSTMHogCNN()
        net.load_state_dict(torch.load('./cptk_lstm_cnn/model_best.pth'))
        seq_len = 5
    elif prj_name == 'lstm_sep':
        net = MindLSTMHog()
        net.load_state_dict(torch.load('./cptk_lstm_sep/model_best.pth'))
        seq_len = 5
    elif prj_name == 'cnn_no_hog':
        net = MindCNNNoHog()
        net.load_state_dict(torch.load('./cptk_cnn_no_hog/model_best.pth'))
        seq_len = 1
    else:
        net = MindLSTMSep()
        net.load_state_dict(torch.load('./cptk_lstm_sep/model_best.pth'))
        seq_len = 5
    if torch.cuda.is_available():
        net.cuda()
    net.eval()
    event_label_path = '/home/shuwen/data/data_preprocessing2/event_classfied_label/'
    reannotation_path = '/home/shuwen/data/data_preprocessing2/regenerate_annotation/'
    annotation_path = '/home/shuwen/data/data_preprocessing2/reformat_annotation/'
    color_img_path = '/home/shuwen/data/data_preprocessing2/annotations/'
    feature_path = '/home/shuwen/data/data_preprocessing2/feature_single/'
    save_path = '/home/shuwen/data/data_preprocessing2/mind_baseline_output/'

    with open('person_id.p', 'rb') as f:
        person_ids = pickle.load(f)
    obj_transforms = transforms.Compose(
        [transforms.Resize([224, 224]),
         transforms.ToTensor(),
         transforms.Normalize(mean=[0.5, 0.5, 0.5],
                              std=[0.5, 0.5, 0.5])])
    clips = os.listdir(event_label_path)
    m1_predict, m1_real = [], []
    m2_predict, m2_real = [], []
    m12_predict, m12_real = [], []
    m21_predict, m21_real = [], []
    mc_predict, mc_real = [], []
    mg_predict, mg_real = [], []
    print(len(mind_test_clips))
    for clip in mind_test_clips:
        if not os.path.exists(reannotation_path + clip):
            continue
        print(clip)
        with open(reannotation_path + clip, 'rb') as f:
            obj_records = pickle.load(f)
        with open(feature_path + clip, 'rb') as f:
            features = pickle.load(f)

        if person_ids[clip.split('.')[0]] == 'P1':
            p1_hog = features[1]
            p2_hog = features[2]
        else:
            p1_hog = features[2]
            p2_hog = features[1]
        annt = pd.read_csv(annotation_path + clip.split('.')[0] + '.txt', sep=",", header=None)
        annt.columns = ["obj_id", "x_min", "y_min", "x_max", "y_max", "frame", "lost", "occluded", "generated", "name",
                        "label"]
        obj_names = annt.name.unique()
        img_names = sorted(glob.glob(color_img_path + clip.split('.')[0] + '/kinect/*.jpg'))
        for obj_name in obj_names:
            if obj_name.startswith('P'):
                continue
            print(obj_name)
            memory = {'mg':{'fluent':None, 'loc':None}, 'mc':{'fluent':None, 'loc':None}, 'm21':{'fluent':None, 'loc':None},
                      'm12': {'fluent': None, 'loc': None}, 'm1':{'fluent':None, 'loc':None}, 'm2':{'fluent':None, 'loc':None}}
            for frame_id in range(len(p1_hog)):

                obj_patch_input = np.zeros((seq_len, 3, 224, 224))
                hog_input = np.zeros((seq_len, 162*2))
                obj_record = obj_records[obj_name][frame_id]

                for mind_name in obj_record:
                    if mind_name == 'm1':
                        m1_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'm2':
                        m2_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'm12':
                        m12_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'm21':
                        m21_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'mc':
                        mc_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'mg':
                        mg_real.append(obj_record[mind_name]['fluent'])

                for i in range(-(seq_len - 1), 1, 1):
                    # hog
                    hog_tracker = p1_hog[frame_id][-162-10:-10]
                    hog_battery = p2_hog[frame_id][-162-10:-10]
                    hog_feature = np.hstack([hog_tracker, hog_battery])
                    hog_input[i + seq_len - 1, :] = hog_feature
                    # obj_patch
                    img = cv2.imread(img_names[frame_id])
                    obj_patch = transforms.ToPILImage()(img)
                    obj_patch = obj_transforms(obj_patch).numpy()
                    obj_patch_input[i + seq_len - 1, ...] = obj_patch


                # get input
                if seq_len > 1:
                    hog_input = torch.from_numpy(hog_input).float().cuda().view((1, seq_len, -1))

                    obj_patch = torch.FloatTensor(obj_patch_input).cuda()
                    obj_patch = obj_patch.view((1, seq_len, 3, 224, 224))
                else:
                    hog_input = torch.from_numpy(hog_input).float().cuda().view((1, -1))

                    obj_patch = torch.FloatTensor(obj_patch_input).cuda()
                    obj_patch = obj_patch.view((1, 3, 224, 224))

                m1, m2, m12, m21, mc = net(obj_patch)
                max_score, idx_mc = torch.max(mc, 1)
                max_score, idx_m21 = torch.max(m21, 1)
                max_score, idx_m12 = torch.max(m12, 1)
                max_score, idx_m1 = torch.max(m1, 1)
                max_score, idx_m2 = torch.max(m2, 1)
                m1_predict.append(idx_m1.cpu().numpy()[0])
                m2_predict.append(idx_m2.cpu().numpy()[0])
                m12_predict.append(idx_m12.cpu().numpy()[0])
                m21_predict.append(idx_m21.cpu().numpy()[0])
                mc_predict.append(idx_mc.cpu().numpy()[0])
                # m1_predict.append(m1.data.cpu().numpy()[0])
                # m2_predict.append(m2.data.cpu().numpy()[0])
                # m12_predict.append(m12.data.cpu().numpy()[0])
                # m21_predict.append(m21.data.cpu().numpy()[0])
                # mc_predict.append(mc.data.cpu().numpy()[0])

    # predict, real = change2vec(mc_predict, mc_real)
    # print(metrics.average_precision_score(real, predict, average = 'weighted'))

    # with open('./cptk_' + prj_name + '/' + 'output_mc.p', 'wb') as f:
    #     pickle.dump([mc_predict, mc_real], f)
    # with open('./cptk_' + prj_name + '/' + 'output_m1.p', 'wb') as f:
    #     pickle.dump([m1_predict, m1_real], f)
    # with open('./cptk_' + prj_name + '/' + 'output_m2.p', 'wb') as f:
    #     pickle.dump([m2_predict, m2_real], f)
    # with open('./cptk_' + prj_name + '/' + 'output_m12.p', 'wb') as f:
    #     pickle.dump([m12_predict, m12_real], f)
    # with open('./cptk_' + prj_name + '/' + 'output_m21.p', 'wb') as f:
    #     pickle.dump([m21_predict, m21_real], f)



    results_mc = metrics.classification_report(mc_real, mc_predict, digits=3)
    results_m1 = metrics.classification_report(m1_real, m1_predict, digits=3)
    results_m2 = metrics.classification_report(m2_real, m2_predict, digits=3)
    results_m12 = metrics.classification_report(m12_real, m12_predict, digits=3)
    results_m21 = metrics.classification_report(m21_real, m21_predict, digits=3)
    print(results_mc)
    print(results_m1)
    print(results_m2)
    print(results_m12)
    print(results_m21)

    cmc = metrics.confusion_matrix(mc_real, mc_predict)
    cm1 = metrics.confusion_matrix(m1_real, m1_predict)
    cm2 = metrics.confusion_matrix(m2_real, m2_predict)
    cm12 = metrics.confusion_matrix(m12_real, m12_predict)
    cm21 = metrics.confusion_matrix(m21_real, m21_predict)
    plot_confusion_matrix(cmc)
    plot_confusion_matrix(cm1)
    plot_confusion_matrix(cm2)
    plot_confusion_matrix(cm12)
    plot_confusion_matrix(cm21)
    score1 = metrics.accuracy_score(mc_real, mc_predict)
    score2 = metrics.accuracy_score(m1_real, m1_predict)
    score3 = metrics.accuracy_score(m2_real, m2_predict)
    score4 = metrics.accuracy_score(m12_real, m12_predict)
    score5 = metrics.accuracy_score(m21_real, m21_predict)
    print([score1, score2, score3, score4, score5])

    with open('./cptk_' + prj_name + '/' + 'seq.p', 'wb') as f:
        pickle.dump([[results_m1, results_m2, results_m12, results_m21, results_mc],
                     [score1, score2, score3, score4, score5], [cmc, cm1, cm2, cm12, cm21]], f)

def test_data_seq_random(prj_name):

    event_label_path = '/home/shuwen/data/data_preprocessing2/event_classfied_label/'
    reannotation_path = '/home/shuwen/data/data_preprocessing2/regenerate_annotation/'
    annotation_path = '/home/shuwen/data/data_preprocessing2/reformat_annotation/'
    color_img_path = '/home/shuwen/data/data_preprocessing2/annotations/'
    feature_path = '/home/shuwen/data/data_preprocessing2/feature_single/'
    save_path = '/home/shuwen/data/data_preprocessing2/mind_baseline_output/'

    with open('person_id.p', 'rb') as f:
        person_ids = pickle.load(f)
    obj_transforms = transforms.Compose(
        [transforms.Resize([224, 224]),
         transforms.ToTensor(),
         transforms.Normalize(mean=[0.5, 0.5, 0.5],
                              std=[0.5, 0.5, 0.5])])
    clips = os.listdir(event_label_path)
    m1_predict, m1_real = [], []
    m2_predict, m2_real = [], []
    m12_predict, m12_real = [], []
    m21_predict, m21_real = [], []
    mc_predict, mc_real = [], []
    mg_predict, mg_real = [], []
    for clip in mind_test_clips:
        if not os.path.exists(reannotation_path + clip):
            continue
        print(clip)
        with open(reannotation_path + clip, 'rb') as f:
            obj_records = pickle.load(f)

        annt = pd.read_csv(annotation_path + clip.split('.')[0] + '.txt', sep=",", header=None)
        annt.columns = ["obj_id", "x_min", "y_min", "x_max", "y_max", "frame", "lost", "occluded", "generated", "name",
                        "label"]
        obj_names = annt.name.unique()
        frames = annt.frame.unique()
        for obj_name in obj_names:
            if obj_name.startswith('P'):
                continue
            print(obj_name)
            memory = {'mg':{'fluent':None, 'loc':None}, 'mc':{'fluent':None, 'loc':None}, 'm21':{'fluent':None, 'loc':None},
                      'm12': {'fluent': None, 'loc': None}, 'm1':{'fluent':None, 'loc':None}, 'm2':{'fluent':None, 'loc':None}}
            for frame_id in range(len(frames)):
                obj_record = obj_records[obj_name][frame_id]
                for mind_name in obj_record:
                    if mind_name == 'm1':
                        m1_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'm2':
                        m2_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'm12':
                        m12_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'm21':
                        m21_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'mc':
                        mc_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'mg':
                        mg_real.append(obj_record[mind_name]['fluent'])

                m1_predict.append(np.random.choice(4, 1))
                m2_predict.append(np.random.choice(4, 1))
                m12_predict.append(np.random.choice(4, 1))
                m21_predict.append(np.random.choice(4, 1))
                mc_predict.append(np.random.choice(4, 1))

    with open('./cptk_' + prj_name + '/' + 'output.p', 'wb') as f:
        pickle.dump({'mc':[mc_predict, mc_real], 'm1':[m1_predict, m1_real], 'm2':[m2_predict, m2_real],
                    'm12':[m12_predict, m12_real], 'm21':[m21_predict, m21_real]}, f)
    results_mc = metrics.classification_report(mc_real, mc_predict, digits=3)
    results_m1 = metrics.classification_report(m1_real, m1_predict, digits=3)
    results_m2 = metrics.classification_report(m2_real, m2_predict, digits=3)
    results_m12 = metrics.classification_report(m12_real, m12_predict, digits=3)
    results_m21 = metrics.classification_report(m21_real, m21_predict, digits=3)
    print(results_mc)
    print(results_m1)
    print(results_m2)
    print(results_m12)
    print(results_m21)

    cmc = metrics.confusion_matrix(mc_real, mc_predict)
    cm1 = metrics.confusion_matrix(m1_real, m1_predict)
    cm2 = metrics.confusion_matrix(m2_real, m2_predict)
    cm12 = metrics.confusion_matrix(m12_real, m12_predict)
    cm21 = metrics.confusion_matrix(m21_real, m21_predict)
    plot_confusion_matrix(cmc)
    plot_confusion_matrix(cm1)
    plot_confusion_matrix(cm2)
    plot_confusion_matrix(cm12)
    plot_confusion_matrix(cm21)
    score1 = metrics.accuracy_score(mc_real, mc_predict)
    score2 = metrics.accuracy_score(m1_real, m1_predict)
    score3 = metrics.accuracy_score(m2_real, m2_predict)
    score4 = metrics.accuracy_score(m12_real, m12_predict)
    score5 = metrics.accuracy_score(m21_real, m21_predict)
    print([score1, score2, score3, score4, score5])

    with open('./cptk_' + prj_name + '/' + 'seq.p', 'wb') as f:
        pickle.dump([[results_m1, results_m2, results_m12, results_m21, results_mc], [score1, score2, score3, score4, score5], [cmc, cm1, cm2, cm12, cm21]], f)

def test_data_seq_tree_search(prj_name):
    # reannotation_path = '/home/shuwen/data/data_preprocessing2/regenerate_annotation/'
    # annotation_path = '/home/shuwen/data/data_preprocessing2/reformat_annotation/'

    path=Path('home')
    reannotation_path=path.reannotation_path
    annotation_path=path.annotation_path

    m1_predict, m1_real = [], []
    m2_predict, m2_real = [], []
    m12_predict, m12_real = [], []
    m21_predict, m21_real = [], []
    mc_predict, mc_real = [], []
    mg_predict, mg_real = [], []
    print(len(mind_test_clips))
    for clip in mind_test_clips:
        if not os.path.exists(reannotation_path + clip):
            continue
        print(clip)
        with open(reannotation_path + clip, 'rb') as f:
            obj_records = pickle.load(f)

        annt = pd.read_csv(annotation_path + clip.split('.')[0] + '.txt', sep=",", header=None)
        annt.columns = ["obj_id", "x_min", "y_min", "x_max", "y_max", "frame", "lost", "occluded", "generated", "name",
                        "label"]
        obj_names = annt.name.unique()
        frames = annt.frame.unique()
        for obj_name in obj_names:
            if obj_name.startswith('P'):
                continue
            print(obj_name)
            with open(os.path.join(path.home_path2, 'mind_posterior_ours_split_steps_0601/') + clip.split('.')[0] + '/' + obj_name + '.p', 'rb') as f:
                search_results = pickle.load(f)

            for frame_id in range(len(frames)):

                obj_record = obj_records[obj_name][frame_id]

                for mind_name in obj_record:
                    if mind_name == 'm1':
                        m1_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'm2':
                        m2_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'm12':
                        m12_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'm21':
                        m21_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'mc':
                        mc_real.append(obj_record[mind_name]['fluent'])
                    elif mind_name == 'mg':
                        mg_real.append(obj_record[mind_name]['fluent'])


                combination = search_results[frame_id]['mind']
                m1_predict.append(combination[1])
                m2_predict.append(combination[2])
                m12_predict.append(combination[3])
                m21_predict.append(combination[4])
                mc_predict.append(combination[0])

    results_mc = metrics.classification_report(mc_real, mc_predict, digits=3)
    results_m1 = metrics.classification_report(m1_real, m1_predict, digits=3)
    results_m2 = metrics.classification_report(m2_real, m2_predict, digits=3)
    results_m12 = metrics.classification_report(m12_real, m12_predict, digits=3)
    results_m21 = metrics.classification_report(m21_real, m21_predict, digits=3)
    print(results_mc)
    print(results_m1)
    print(results_m2)
    print(results_m12)
    print(results_m21)

    cmc = metrics.confusion_matrix(mc_real, mc_predict)
    cm1 = metrics.confusion_matrix(m1_real, m1_predict)
    cm2 = metrics.confusion_matrix(m2_real, m2_predict)
    cm12 = metrics.confusion_matrix(m12_real, m12_predict)
    cm21 = metrics.confusion_matrix(m21_real, m21_predict)
    plot_confusion_matrix(cmc)
    plot_confusion_matrix(cm1)
    plot_confusion_matrix(cm2)
    plot_confusion_matrix(cm12)
    plot_confusion_matrix(cm21)
    score1 = metrics.accuracy_score(mc_real, mc_predict)
    score2 = metrics.accuracy_score(m1_real, m1_predict)
    score3 = metrics.accuracy_score(m2_real, m2_predict)
    score4 = metrics.accuracy_score(m12_real, m12_predict)
    score5 = metrics.accuracy_score(m21_real, m21_predict)
    print([score1, score2, score3, score4, score5])

    # with open('./cptk_' + prj_name + '/' + 'seq_0601.p', 'wb') as f:
    #     pickle.dump([[results_m1, results_m2, results_m12, results_m21, results_mc],
    #                  [score1, score2, score3, score4, score5], [cmc, cm1, cm2, cm12, cm21]], f)


if __name__ == '__main__':
    # main()
    test_data_seq_tree_search('split_clips')









