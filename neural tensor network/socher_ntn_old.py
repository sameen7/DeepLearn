# -*- coding: utf-8 -*-

import glob
import ntn_input
from lib.attention import *
from lib import utility
from lib.ntn import *
import random
import keras

dimx,dimy = 100,100
corrupt_samples = 1
thres = 0.023

warnings.simplefilter("ignore")

'''def word2vec_embedding_layer(embedding_matrix):
    #weights = np.load('Word2Vec_QA.syn0.npy')
    layer = Embedding(input_dim=embedding_matrix.shape[0], output_dim=embedding_matrix.shape[1], weights=[embedding_matrix])
    return layer

try:
    word = wordVec_model['word']
    print 'using loaded model.....'
except:
    wordVec_model = gen.models.KeyedVectors.load_word2vec_format("I:\\workspace\\neural network\\cornet_evals\\sick\\GoogleNews-vectors-negative300.bin.gz",binary=True)
'''

def contrastive_loss(y_true, y_pred):
    margin = 1
    return K.mean(y_true * K.square(y_pred) +
                  (1 - y_true) * K.square(K.maximum(margin - y_pred, 0)))

def max_margin(y_true, y_pred):
    num_ex = y_pred.shape[0]/2
    #print num_ex 
    y_pos = y_pred[:num_ex]
    y_neg = y_pred[num_ex:]
    return K.mean(K.maximum(0., 1. - y_pos + y_neg))

def data_to_indexed(data, entities, relations):
    entity_to_index = {entities[i] : i for i in range(len(entities))}
    relation_to_index = {relations[i] : i for i in range(len(relations))}
    indexed_data = [(entity_to_index[data[i][0]], relation_to_index[data[i][1]],\
            entity_to_index[data[i][2]]) for i in range(len(data))]
    return indexed_data

def get_batch(batch_size, data, num_entities, corrupt_size):
    random_indices = random.sample(range(len(data)), batch_size)
    #data[i][0] = e1, data[i][1] = r, data[i][2] = e2, random=e3 (corrupted)
    batch = [(data[i][0], data[i][1], data[i][2], random.randint(0, num_entities-1))\
             for i in random_indices for j in range(corrupt_size)]
    return batch

def split_batch(data_batch, num_relations):
    batches = [[] for i in range(num_relations)]
    for e1,r,e2,e3 in data_batch:
        batches[r].append((e1,e2,e3))
    return batches

def make_batch(e1,e2,rel,batch_size=100):
    new_e1,new_e2,new_rel,labels = [],[],[],[]
    split = batch_size/2
    mid = (len(e1) - len(e1) % batch_size) / 2
    for i in range(0,mid-1,split):
        new_e1.extend(e1[i:i+split])
        new_e2.extend(e2[i:i+split])
        new_rel.extend(rel[i:i+split])
        new_e1.extend(e1[mid+i:mid+i+split])
        new_e2.extend(e2[mid+i:mid+i+split])
        new_rel.extend(rel[mid+i:mid+i+split])
        labels.extend([1]*split)
        labels.extend([0]*split)
    return new_e1,new_e2,new_rel,labels
    
def fill_entity(e1,e2,max_num):
    for key in e1:
        if len(e1[key])<max_num:
            entity_len = len(e1[key])
            train_samples = max_num - entity_len
            #print entity_len, max_num
            samples = []
            for j in range(train_samples):
                samples.append(random.randrange(0,entity_len))
            for i in samples:
                e1[key].append(e1[key][i])
                e2[key].append(e2[key][i])
    return e1,e2

def prepare_data():
    raw_training_data = ntn_input.load_training_data(ntn_input.data_path)
    raw_dev_data = ntn_input.load_dev_data(ntn_input.data_path)
    print("Load entities and relations...")
    entities_list = ntn_input.load_entities(ntn_input.data_path)
    relations_list = ntn_input.load_relations(ntn_input.data_path)
    #python list of (e1, R, e2) for entire training set in index form
    indexed_training_data = data_to_indexed(raw_training_data, entities_list, relations_list)
    indexed_dev_data = data_to_indexed(raw_dev_data, entities_list, relations_list)
    print("Load embeddings...")
    (init_word_embeds, entity_to_wordvec) = ntn_input.load_init_embeds(ntn_input.data_path)

    num_entities = len(entities_list)
    num_relations = len(relations_list)
    
    e1,e2,labels_train,labels_dev,t1,t2 = {},{},[],[],{},{}
    
    for i in indexed_training_data:
        try:
            e1[i[1]].append(init_word_embeds[i[0]])
            e2[i[1]].append(init_word_embeds[i[2]])
        except:
            e1[i[1]] = []
            e2[i[1]] = []
            
    max_len_e1 = max([len(e1[i])for i in e1])
    labels_train = [1]*max_len_e1
    e1,e2 = fill_entity(e1,e2,max_len_e1)
    #bre
    for i in range(max_len_e1):
        for j in range(corrupt_samples):
            for k in range(11):
                e1[k].append(init_word_embeds[indexed_training_data[i][0]])
                e2[k].append(init_word_embeds[random.randrange(0,len(init_word_embeds))])
        labels_train.append(0)

    for i in indexed_dev_data:
        try:
            t1[i[1]].append(init_word_embeds[i[0]])
            t2[i[1]].append(init_word_embeds[i[2]])
        except:
            t1[i[1]] = []
            t2[i[1]] = []
            
    max_len_t1 = max([len(t1[i])for i in t1])
    labels_dev = [1]*max_len_t1
    
    t1,t2 = fill_entity(t1,t2,max_len_t1)

    for i in range(max_len_t1):
        for j in range(corrupt_samples):
            for k in range(11):
                t1[k].append(init_word_embeds[indexed_dev_data[i][0]])
                dev_reltn.append(init_word_embeds[indexed_dev_data[i][1]])
                t2[k].append(init_word_embeds[neg_samples[i*corrupt_samples+j]])
        labels_dev.append(0)

    labels_train,labels_dev = np.array(labels_train),np.array(labels_dev)
   
    return e1,e2,labels_train,t1,t2,labels_dev,num_relations

class selective_train(Layer):
    def __init__(self, out_ntn=1,in_ntn=100, **kwargs):
        super(selective_train, self).__init__(**kwargs)
        self.out_ntn = out_ntn

    def call(self, inputs):
        #product = ntn_product[k[0]]
        #return product
        k = inputs[0]
        k1 = inputs[1]
        ntn = ntn_layer(inp_size=dimx,out_size=4,name=name)([inpx,inpy])
        #print k
        if k == 1:
            print 'here'
        return k

    def compute_output_shape(self, input_shape):
        print 'input shape:',input_shape
        #out_shape = 
        #out_shape  = list(input_shape[0])
        #out_shape[-1] = 1
        #print 'output shape:',out_shape
        #return (input_shape[0][0],self.out_ntn)
        return input_shape

e1,e2,labels_train,t1,t2,labels_dev,num_relations = prepare_data()

bre

if True:
    
    Input_x, Input_y = [], []
    #inpx = Input(shape=(dimx,))
    #inpy = Input(shape=(dimy,))
    for i in range(num_relations):
        Input_x.append(Input(shape=(dimx,)))
        Input_y.append(Input(shape=(dimy,)))
        
    #ntn = {}
    ntn = []
    for i in range(num_relations):
        name = 'ntn'+str(i)
        #ntn[i] = ntn_layer(inp_size=dimx,out_size=4,name=name)([inpx,inpy])
        ntn.append(ntn_layer(inp_size=dimx,out_size=4)([Input_x[i],Input_y[i]]))
    
    #ntn = ntn_layer(inp_size=dimx,out_size=4,activation=None)([hx,hy])
    #ntn = Merge(mode="concat",name='h')([hx,hy])
    #ntn = Dense(20,activation='sigmoid')(ntn)
    #score1 = Dense(1,activation='tanh')(ntn[0])
    #score2 = Dense(1,activation='tanh')(ntn[1])
    merge_model = Merge(mode='concat')([ntn[i]for i in range(num_relations)])
    #score = Merge(mode='sum')([score1,score2])
    #score_rel_k = selective_train()([rel,rel])
    #score = Dense(1,activation='tanh')(score_rel_k)
    
    score = Dense(num_relations,activation='softmax')(merge_model)
    
    all_inputs = [Input_x[i]for i in range(num_relations)]
    all_inputs.extend([Input_y[i]for i in range(num_relations)])
    
    model = Model(all_inputs,score)
    
    model.compile(loss=max_margin,optimizer='adam')
    print("Build Model...")
    
    model.fit([e1,e2,kup],
                 labels_train,
                 nb_epoch=1,
                 batch_size=100,verbose=1) 
    v1 = model.predict([t1,t2,dev_reltn])
    pred = []
    for i in v1:
        if i>thres:
            pred.append(1)
        else:
            pred.append(0)

    pos,neg = 0,0
    for i in range(0,len(pred)):
        if pred[i] == labels_dev[i]:
            pos = pos+1
        else:
            neg = neg+1
    print "percentage(%) accuracy   --> ",(float(pos)/float(len(pred)))*100# -*- coding: utf-8 -*-
