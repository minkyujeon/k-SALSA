import os
import sys
import random

import torch
import numpy as np
from torch.utils.tensorboard import SummaryWriter
import torch
import torch.nn as nn
import torch.nn.functional as F 
from utils.func import *
from train import train, evaluate
from utils.metrics import Estimator
from data.builder import generate_dataset
from data.transforms import data_transforms, simple_transform
from modules.builder import generate_model
from torch.utils.data import Dataset,DataLoader
import PIL.Image as Image
import pandas as pd
from collections import Counter
import wandb
import argparse
import pdb

class aptos_centroid_dataset(Dataset): # Inherits from the Dataset class.
    '''
    dataset class overloads the __init__, __len__, __getitem__ methods of the Dataset class. 
    
    Attributes :
        df:  DataFrame object for the csv file.
        data_path: Location of the dataset.
        image_transform: Transformations to apply to the image.
        train: A boolean indicating whether it is a training_set or not.
    '''
    
    def __init__(self,df,fname_lst,data_path,labels,image_transform=None): # Constructor.
        super(Dataset,self).__init__() #Calls the constructor of the Dataset class.
        self.fname_lst = fname_lst
        self.data_path = data_path
        self.image_transform = image_transform
        self.labels = labels
        # self.normalized_labels = normalized_labels
        
    def __len__(self):
        return len(self.fname_lst) #Returns the number of samples in the dataset.
    
    def __getitem__(self,index):
        image_id = self.fname_lst[index]
        image = Image.open(f'{self.data_path}/{image_id}_centroids.png') #Image.
        if self.image_transform :
            image = self.image_transform(image) #Applies transformation to the image.
        label = self.labels[index]

        # label = self.df['diagnosis'][index] #self.normalized_labels[index]
        return image,label #,image_id,index #If train == True, return image & label.

            
class aptos_dataset(Dataset): # Inherits from the Dataset class.
    '''
    dataset class overloads the __init__, __len__, __getitem__ methods of the Dataset class. 
    
    Attributes :
        df:  DataFrame object for the csv file.
        data_path: Location of the dataset.
        image_transform: Transformations to apply to the image.
        train: A boolean indicating whether it is a training_set or not.
    '''
    
    def __init__(self,df,data_path,image_transform=None): # Constructor.
        super(Dataset,self).__init__() #Calls the constructor of the Dataset class.
        self.df = df
        self.data_path = data_path
        self.image_transform = image_transform
        
    def __len__(self):
        return len(self.df) #Returns the number of samples in the dataset.
    
    def __getitem__(self,index):
        # print('index:',index)
        # print('self.df[id_code]:',self.df['id_code'])
        image_id = self.df['id_code'][index]
        image = Image.open(f'{self.data_path}/{image_id}.png') #Image.
        if self.image_transform :
            image = self.image_transform(image) #Applies transformation to the image.
        
        label = self.df['diagnosis'][index] #Label.
        return image,label #If train == True, return image & label.

def make_labels(df, group_by_centers, data_name='aptos'):
    labels_lst = []
    fname_lst = []
    for i in range(len(group_by_centers)):
        i=i+1 # i+1 주의!!!
        fname = np.asarray((group_by_centers['id_code']))[i-1][1].iloc[0]
        fname_lst.append(fname)
        a = df[df['centers']==i]
        if data_name == 'eyepacs':
            a_array = np.asarray(a['level'])
        else:
            a_array = np.asarray(a['diagnosis'])
        cluster_label = Counter(a_array)
        labels = np.zeros([5])
        
        for j in range(5):
            labels[j] = cluster_label[j]
        labels_lst.append(labels) # 해당 class위치에 갯수
        
    labels_npy = np.asarray(labels_lst)
    labels_tensor = torch.from_numpy(labels_npy)
#     print('labels_tensor:',labels_tensor)
    normalized_labels = F.softmax(labels_tensor)
#     print('normalized_labels:',normalized_labels)

    normalized_labels_npy = np.asarray(normalized_labels)
    return normalized_labels_npy, fname_lst

        
def epi(trial):
#     parser = argparse.ArgumentParser(description="args2")
    # environment
    args = parse_config()
    cfg = load_config(args.config)

    wandb.init(project="aptos_cls_centroid_v0", entity="eccv2022_")
    ################################################
    ############ CHECK
    ###############################################
    img_type = args.k + '_' + args.crop + '_' + args.lambda1 + '_' + args.lambda2 
    
    # create folder
    cfg.base.save_path = cfg.base.save_path  + '_' + img_type + '_' + str(trial) + 'centroid' +'tmp'
    save_path = cfg.base.save_path 
    cfg.base.log_path = cfg.base.log_path  + '_' + img_type + '_' + str(trial)+ 'centroid' +'tmp'
    log_path = cfg.base.log_path 
    ################################################
    ############ CHECK
    ###############################################
    wandb.config = {
        "dataname": args.config,
        "k": args.k,
        "crop": args.crop,
        "lambda1": args.lambda1,
        "lambda2": args.lambda2
    }

#     pdb.set_trace()
    if os.path.exists(save_path):
        warning = 'Save path {} exists.\nDo you want to overwrite it? (y/n)\n'.format(save_path)
        if not (args.overwrite or input(warning) == 'y'):
            sys.exit(0)
    else:
        os.makedirs(save_path)

    logger = SummaryWriter(log_path)
    copy_config(args.config, save_path)

    # print configuration
    if args.print_config:
        print_config({
            'BASE CONFIG': cfg.base,
            'DATA CONFIG': cfg.data,
            'TRAIN CONFIG': cfg.train
        })
    else:
        print_msg('LOADING CONFIG FILE: {}'.format(args.config))

    # train
    # set_random_seed(cfg.base.random_seed)
    model = generate_model(cfg)

    # cfg.data.mean = mean
    # cfg.data.std = std

    train_transform, test_transform = data_transforms(cfg)

#     pdb.set_trace()
# '/home/minkyu/privacy/ECCV2022/nearest_neighbor_samesize/ECCV_aptos_k5_nearest_samesize/inference_results/4/215d2b7c3fde.png' 

    ################################################
    ############ CHECK
    ###############################################
    # images_path = '/home/minkyu/privacy/ECCV2022/nearest_neighbor_samesize/eccv_nearest_aptos_'+img_type+'/centroid'

#     images_path = '/home/minkyu/privacy/ECCV2022/nearest_neighbor_samesize/ECCV_aptos_k5_nearest_samesize/inference_results/4'
    images_path = '/home/minkyu/privacy/ECCV2022/nearest_neighbor_samesize/eccv_nearest_aptos_k2_crop4_1e2_1e-6/centroid'


    # Make labels
    # aptos_df = pd.read_csv('/home/minkyu/privacy/ECCV2022/nearest_neighbor_samesize/ECCV/aptos/nearest_neighbor_centroid/labels/'+args.k+'_aptos_nearest_df.csv')
    aptos_df = pd.read_csv('/home/minkyu/privacy/ECCV2022/nearest_neighbor_samesize/ECCV/aptos/nearest_neighbor_centroid/labels/k2_aptos_nearest_df.csv')
    print(f'No.of.training_samples: {len(aptos_df)}')
    ################################################
    ############ CHECK
    ###############################################

    aptos_label_csv = pd.read_csv('/hub_data/privacy/ECCV/data/splited_val/aptos/aptos_val_3000.csv')
#     pdb.set_trace()
    
#     print([aptos_label_csv['level'].tolist().count(i)/10000 for i in range(5)])
#     pdb.set_trace()
    df_aptos_merge = pd.merge(aptos_df, aptos_label_csv, on='id_code')
    # df_k5_aptos_W16.to_csv('./labels/df_k5_aptos_w16.csv')
    group_by_centers_aptos = df_aptos_merge.groupby(['centers'])
    aptos_normalized_labels_npy, fname_lst = make_labels(df_aptos_merge, group_by_centers_aptos, data_name='aptos')
    label_dist = aptos_normalized_labels_npy
    max_label = torch.max(torch.tensor(label_dist),1)[1]
    print([max_label.tolist().count(i)/len(max_label) for i in range(5)])
#     pdb.set_trace(
    print('group_by_centers_aptos:',len(group_by_centers_aptos))
    print('fname_lst:', len(fname_lst))

    # normalized_labels = np.load('/home/minkyu/privacy/ICML2022/classification/labels/aptos/whole_k5_aptos_W16_normalized_labels.npy')
    # train_dataset = aptos_centroid_dataset(train_df,images_path,normalized_labels,image_transform=train_transform)
    train_dataset = aptos_centroid_dataset(aptos_df,fname_lst,images_path,aptos_normalized_labels_npy,image_transform=train_transform)

    test_df = pd.read_csv('/hub_data/privacy/ECCV/data/splited_val/aptos/val_splited.csv')
    test_image_path = '/hub_data/privacy/ECCV/data/splited_val/aptos/aptos_val/val'
    
    val_dataset = aptos_dataset(test_df, test_image_path, image_transform=test_transform)
    test_dataset = aptos_dataset(test_df, test_image_path, image_transform=test_transform)

    estimator = Estimator(cfg.train.criterion, cfg.data.num_classes)
    
    train(
        cfg=cfg,
        model=model,
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        estimator=estimator,
        logger=logger
    )

    # test
    print('This is the performance of the best validation model:')
    checkpoint = os.path.join(save_path, 'best_validation_weights.pt')
    acc, kappa, confusion_matrix = evaluate(args, cfg, model, checkpoint, test_dataset, estimator)
    print('This is the performance of the final model:')
    checkpoint = os.path.join(save_path, 'final_weights.pt')
    test_acc, test_kappa, test_confusion_matrix = evaluate(args, cfg, model, checkpoint, test_dataset, estimator)

    return test_acc, test_kappa, test_confusion_matrix, args.k , args.crop, args.lambda1 , args.lambda2 
    
def main():
    
    acc_lst = []
    kappa_lst = []
    confusion_matrix_lst = []
    
    for trial in range(2):
        test_acc, test_kappa, test_confusion_matrix, k , crop, lambda1 , lambda2  = epi(trial)
        acc_lst.append(test_acc)
        kappa_lst.append(test_kappa)
        confusion_matrix_lst.append(test_confusion_matrix)
        
    print('acc: ', acc_lst)
    print('kappa: ', kappa_lst)
    print('confusion_matrix: ', confusion_matrix_lst)
    
    wandb.log({"acc": np.mean(acc_lst),
               "kappa": np.mean(kappa_lst), 
               "k": k,
               "crop": crop,
               "lambda1": lambda1,
               "lambda2": lambda2})
    
def set_random_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.deterministic = True


if __name__ == '__main__':
    main()
