import tensorflow as tf
import numpy as np


class TextCNN(object):
    """
    A CNN for text classification.
    Uses an embedding layer, followed by a convolutional, max-pooling and softmax layer.
    为了接收各种参数我们把结构放入textCNN类中，生成model graph在init函数
    """
    def __init__(self, sequence_length, num_classes, vocab_size,embedding_size, filter_sizes, num_filters, l2_reg_lambda=0.0):

        """
        sequence_length – The length of our sentences.我们将填充我们的句子去拥有相同的长度（59） 
        num_classes – Number of classes in the output layer, two in our case (positive and negative).
        vocab_size – The size of our vocabulary. This is needed to define the size of our embedding layer, 
        which will have shape [vocabulary_size, embedding_size].
        embedding_size – The dimensionality of our embeddings.
        filter_sizes – The number of words we want our convolutional filters to cover. 
        num_filters – The number of filters per filter size
        """

        #这里介绍了三个placeholder占位符，
        # Placeholders for input, output and dropout
        #input_y Means output layer
        self.input_x = tf.placeholder(tf.int32, [None, sequence_length], name="input_x")
        #placeholder to create the graph to set the sequence_length as the input which should be like 59(the maximum words in the dataset.)

        self.input_y = tf.placeholder(tf.float32, [None, num_classes], name="input_y")
        #placeholder to create the graph to set the num_classes which should be like 2 

        self.dropout_keep_prob = tf.placeholder(tf.float32, name="dropout_keep_prob")
        #probability of keeping a neuron in the dropout layer
        '''
        tf.placeholder creates a placeholder variable that we feed to the network when we execute it at train or test time.
        '''
        # Keeping track of l2 regularization loss (optional)
        l2_loss = tf.constant(0.0)

        # Embedding layer
        #first layer is the Embedding layer, which maps vocabulary word indices into low-dimensional vector representations.
        #第一次结构，将单词转换为低纬的向量表示。
        with tf.device('/cpu:0'), tf.name_scope("embedding"):
            #tf.device("/cpu:0") forces an operation to be executed on the CPU.
            #tf.name_scope creates a new Name Scope with the name “embedding”.
            #W is our embedding matrix that we learn during training.
            # We initialize it using a random uniform distribution.  
            self.W = tf.Variable(
                tf.random_uniform([vocab_size, embedding_size], -1.0, 1.0),
                name="W")
            #tf.random_uniform(shape,minval=0,maxval=None,dtype=tf.float32,seed=None,name=None):用于生成随机数tensor的，均匀分布随机数，min到max

            # tf.nn.embedding_lookup 创造实际的嵌入式操作，其结果是3维的张量， [None, sequence_length, embedding_size]
            self.embedded_chars = tf.nn.embedding_lookup(self.W, self.input_x)
            #因为在我们的conv2d中，需要的是4维的tensor，所以在这里我们需要一个expand维度的操作， 
            #在最后加一个维度是in_channel，但是，我们的embedding没有channal，所以1就好
            self.embedded_chars_expanded = tf.expand_dims(self.embedded_chars, -1)





        #现在来创建我们的convolution layers，我们使用不同size的filter，卷积将会创造出不同的tensor，
        #我们需要iterate它们，然后创造一个layer，然后将它们合并成一个大的特征向量
        # Create a convolution + maxpool layer for each filter size
        
        pooled_outputs = []
        for i, filter_size in enumerate(filter_sizes):
            with tf.name_scope("conv-maxpool-%s" % filter_size):
                # Convolution Layer
                filter_shape = [filter_size, embedding_size, 1, num_filters]
                W = tf.Variable(tf.truncated_normal(filter_shape, stddev=0.1), name="W")
                b = tf.Variable(tf.constant(0.1, shape=[num_filters]), name="b")
                conv = tf.nn.conv2d(
                    self.embedded_chars_expanded, #[None, sequence_length, embedding_size, 1]
                    W, 
                    strides=[1, 1, 1, 1],
                    padding="VALID",
                    name="conv")
                # Apply nonlinearity
                h = tf.nn.relu(tf.nn.bias_add(conv, b), name="relu")
                # Maxpooling over the outputs
                pooled = tf.nn.max_pool(
                    h,
                    ksize=[1, sequence_length - filter_size + 1, 1, 1],
                    strides=[1, 1, 1, 1],
                    padding='VALID',
                    name="pool")
                pooled_outputs.append(pooled)

        # Combine all the pooled features
        num_filters_total = num_filters * len(filter_sizes)
        self.h_pool = tf.concat(pooled_outputs, 3)
        self.h_pool_flat = tf.reshape(self.h_pool, [-1, num_filters_total])











        # Add dropout
        with tf.name_scope("dropout"):
            self.h_drop = tf.nn.dropout(self.h_pool_flat, self.dropout_keep_prob)

        # Final (unnormalized) scores and predictions
        with tf.name_scope("output"):
            W = tf.get_variable(
                "W",
                shape=[num_filters_total, num_classes],
                initializer=tf.contrib.layers.xavier_initializer())
            b = tf.Variable(tf.constant(0.1, shape=[num_classes]), name="b")
            l2_loss += tf.nn.l2_loss(W)
            l2_loss += tf.nn.l2_loss(b)
            self.scores = tf.nn.xw_plus_b(self.h_drop, W, b, name="scores")
            self.predictions = tf.argmax(self.scores, 1, name="predictions")


        # CalculateMean cross-entropy loss
        with tf.name_scope("loss"):
            losses = tf.nn.softmax_cross_entropy_with_logits(logits=self.scores, labels=self.input_y)
            self.loss = tf.reduce_mean(losses) + l2_reg_lambda * l2_loss

        # Accuracy
        with tf.name_scope("accuracy"):
            correct_predictions = tf.equal(self.predictions, tf.argmax(self.input_y, 1))
            self.accuracy = tf.reduce_mean(tf.cast(correct_predictions, "float"), name="accuracy")
