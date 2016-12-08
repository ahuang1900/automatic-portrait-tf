import numpy as np
import os
import scipy.io
import scipy.misc
import tensorflow as tf
import random

from net import FCN8s


COLOR_SET = [
    [255, 255, 255], [125, 135, 185], [190, 193, 212], [214, 188, 192],
    [187, 119, 132], [142, 6, 59], [74, 111, 227], [133, 149, 225],
    [181, 187, 227], [230, 175, 185], [224, 123, 145], [211, 63, 106],
    [17, 198, 56], [141, 213, 147], [198, 222, 199], [234, 211, 198],
    [240, 185, 141], [239, 151, 8], [15, 207, 192], [156, 222, 214],
    [213, 234, 231], [243, 225, 235], [246, 196, 225], [247, 156, 212]
]


LAYER_ID_MAP = {
    'conv1_1': [2, True],
    'conv1_2': [4, True],

    'conv2_1': [7, True],
    'conv2_2': [9, True],

    'conv3_1': [12, True],
    'conv3_2': [14, True],
    'conv3_3': [16, True],

    'conv4_1': [20, True],
    'conv4_2': [22, True],
    'conv4_3': [24, True],

    'conv5_1': [28, True],
    'conv5_2': [30, True],
    'conv5_3': [32, True],

    'fc6': [35, True],
    'fc7': [37, True],

    'score_fr': [39, True],

    'upscore2': [40, False],
    'score_pool4': [42, True],

    'upscore_pool4': [45, False],
    'score_pool3': [47, True],

    'upscore8': [50, False],
}


def load_caffe_model():
    model_weight = 'fcn8s-heavy-pascal.mat'
    return np.load(model_weight)


def build_image(filename):
    MEAN_VALUES = np.array([104.00698793, 116.66876762, 122.67891434])
    MEAN_VALUES = MEAN_VALUES..reshape((1, 1, 1, 3))
    img = scipy.misc.imread(filename, mode='RGB')[:, :, ::-1]
    height, width, _ = img.shape
    img = np.reshape(img, (1, height, width, 3)) - MEAN_VALUES
    return img


def save_image(result, filename):
    s = set()
    _, h, w = result.shape
    result = result.reshape(h*w)
    image = []
    for v in result:
        image.append(COLOR_SET[v])
        if v not in s:
            s.add(v)
    image = np.array(image)
    image = np.reshape(image, (h, w, 3))
    scipy.misc.imsave(filename, image)


def train(net):
    TRAIN_IMAGE_DIRECTORY = './data/images_data_crop'
    MASK_DIRECTORY = './data/images_mask'
    BATCH_SIZE = 5

    with tf.Session() as sess:
        global_step = tf.Variable(0, name='global_step', trainable=False)

        saver = tf.train.Saver(tf.all_variables())
        model_file = tf.train.latest_checkpoint('./model/')
        if model_file:
            print('Restore from {}'.format(model_file))
            saver.restore(sess, model_file)
        else:
            print('Initialize')
            sess.run(tf.initialize_all_variables())
            fcn.set_default_value(sess, load_caffe_model(), LAYER_ID_MAP)

        print('Start')
        label = tf.placeholder(tf.uint8, shape=[None, None, None])
        cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(
            tf.reshape(net['score'], [-1, 2]),
            tf.one_hot(tf.reshape(label, [-1]), 2)))
        optimizer = tf.train.GradientDescentOptimizer(1e-4)
        train_op = optimizer.minimize(cost, global_step=global_step)

        all_images = os.listdir(TRAIN_IMAGE_DIRECTORY)
        while True:
            image_mat = []
            label_mat = []
            images = random.sample(all_images, BATCH_SIZE)
            for image_name in images:
                name = image_name.split('.')[0]
                image_path = os.path.join(TRAIN_IMAGE_DIRECTORY, image_name)
                mask_name = '%s_mask.mat' % name
                mask_path = os.path.join(MASK_DIRECTORY, mask_name)
                image_mat.append(build_image(image_path))
                label_mat.append(scipy.io.loadmat(mask_path)['mask'])

            feed_dict = {
                net['image']: np.concatenate(image_mat),
                net['drop_rate']: 0.5,
                label: np.stack(label_mat)
            }
            _, loss, step = sess.run([train_op, cost, global_step],
                                     feed_dict=feed_dict)

            if step % 10 == 0:
                print(step, loss)
            if step % 500 == 0:
                saver.save(sess, './model/PortraitFCN', global_step=step)
                print('Saved, step %d' % step)
            if step >= 100000:
                break


def test(net, image_name):
    image = build_image(image_name)

    with tf.Session() as sess:
        saver = tf.train.Saver(tf.all_variables())
        model_file = tf.train.latest_checkpoint('./model/')
        if model_file:
            saver.restore(sess, model_file)
        else:
            sess.run(tf.initialize_all_variables())
            fcn.set_default_value(sess, load_caffe_model(), LAYER_ID_MAP)

        feed_dict = {
            net['image']: image,
            net['drop_rate']: 1
        }
        result = sess.run(tf.argmax(net['score'], dimension=3),
                          feed_dict=feed_dict)
    return result


if __name__ == '__main__':
    fcn = FCN8s(2)
    train(fcn.net)
    save_image(test(fcn.net, '00015.png'), 'result.png')
