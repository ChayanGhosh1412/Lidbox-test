
from tensorflow.keras.layers import (
    Activation,
    BatchNormalization,
    Conv1D,
    Dense,
    Dropout,
    Input,
    Layer,
    SpatialDropout1D,
)
from tensorflow.keras.models import Model
import tensorflow as tf

TIME_AXIS = 1
STDDEV_SQRT_MIN_CLIP = 1e-10


class GlobalMeanStddevPooling1D(Layer):
    """
    Compute arithmetic mean and standard deviation of the inputs along the time steps dimension,
    then output the concatenation of the computed stats.
    """
    def call(self, inputs):
        means = tf.math.reduce_mean(inputs, axis=TIME_AXIS, keepdims=True)
        variances = tf.math.reduce_mean(tf.math.square(inputs - means), axis=TIME_AXIS)
        means = tf.squeeze(means, TIME_AXIS)
        stddevs = tf.math.sqrt(tf.clip_by_value(variances, STDDEV_SQRT_MIN_CLIP, variances.dtype.max))
        return tf.concat((means, stddevs), axis=TIME_AXIS)


def frame_layer(filters, kernel_size, strides, padding="causal", activation="relu", name="frame"):
    return Conv1D(filters, kernel_size, strides, padding=padding, activation=activation, name=name)


def segment_layer(units, activation="relu", name="segment"):
    return Dense(units, activation=activation, name=name)


def create(input_shape, num_outputs, channel_dropout_rate=0, name="x-vector"):
    inputs = Input(shape=input_shape, name="input")

    x = inputs
    if channel_dropout_rate > 0:
        x = SpatialDropout1D(channel_dropout_rate, name="channel_dropout")(x)

    x = frame_layer(512,  5, 1, name="frame1")(x)
    x = frame_layer(512,  3, 2, name="frame2")(x)
    x = frame_layer(512,  3, 3, name="frame3")(x)
    x = frame_layer(512,  1, 1, name="frame4")(x)
    x = frame_layer(1500, 1, 1, name="frame5")(x)

    x = GlobalMeanStddevPooling1D(name="stats_pooling")(x)

    x = segment_layer(512, name="segment1")(x)
    x = segment_layer(512, name="segment2")(x)

    x = Dense(num_outputs, activation=None, name="outputs")(x)
    outputs = Activation(tf.nn.log_softmax, name="log_softmax")(x)

    return Model(inputs=inputs, outputs=outputs, name=name)


def as_embedding_extractor(m):
    l = m.get_layer(name="segment1")
    l.activation = None
    return Model(inputs=m.inputs, outputs=l.output)
