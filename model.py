import tensorflow as tf

import os
import time

from matplotlib import pyplot as plt

from Generator import buildGenerator
from Discriminator import buildDiscriminator
import scipy.signal as scig
import numpy as np
import scipy 
from PIL import Image

tf.compat.v1.enable_eager_execution()

# Change PATH variable to absolute/ relative path to the images directory on your machine which contains the train and val folders
PATH = '/Users/aman/Downloads/data' 

# Change these variables as per your need
EPOCHS = 100
BUFFER_SIZE = 14224
BATCH_SIZE = 4
IMG_WIDTH = 256
IMG_HEIGHT = 256

sigma = 30
x = np.arange(0, 256) - 128
X,Y = np.meshgrid(x,x)
kernel = 1/(sigma**2 *2*np.pi) * np.exp(-1/2 *(X**2 + Y**2)/sigma**2)
kernel3 = np.repeat(np.expand_dims(kernel,2),3,2)
kernel_size =3

def apply_result_hue_to_input(input_image, result_image):

    blurred_result = gaussian_filter(result_image, sigma=kernel_size)

    # Normalize blurred result to [0, 1]
    blurred_result = blurred_result / np.max(blurred_result)

    # Expand blurred result to match input image shape (for color images)
    expanded_blurred = np.stack([blurred_result] * input_image.shape[-1], axis=-1)

    # Add blurred result to input image
    combined_image = input_image + expanded_blurred

    return combined_image


def load(image_file):
    image = tf.io.read_file(image_file)
    image = tf.image.decode_png(image)

    w = tf.shape(image)[1]

    w = w // 2
    real_image = image[:, :w, :]
    input_image = image[:, w:, :]

    input_image = tf.cast(input_image, tf.float32)
    real_image = tf.cast(real_image, tf.float32)

    #input_image = apply_result_hue_to_input(input_image, real_image)

    return input_image, real_image

def load_single(image_file):

    image = tf.io.read_file(image_file)
    image = tf.image.decode_png(image)

    image = tf.cast(image, tf.float32)

    return image


def resize(input_image, real_image, height, width):
    input_image = tf.image.resize(input_image, [height, width],
                                method=tf.image.ResizeMethod.NEAREST_NEIGHBOR)
    real_image = tf.image.resize(real_image, [height, width],
                               method=tf.image.ResizeMethod.NEAREST_NEIGHBOR)

    return input_image, real_image

def random_crop(input_image, real_image):
    stacked_image = tf.stack([input_image, real_image], axis=0)
    cropped_image = tf.image.random_crop(
      stacked_image, size=[2, IMG_HEIGHT, IMG_WIDTH, 3])

    return cropped_image[0], cropped_image[1]

def normalize(input_image, real_image):
    input_image = (input_image / 127.5) - 1
    real_image = (real_image / 127.5) - 1

    return input_image, real_image

@tf.function()
def random_jitter(input_image, real_image):
    input_image, real_image = resize(input_image, real_image, 286, 286)
    input_image, real_image = random_crop(input_image, real_image)

    if tf.random.uniform(()) > 0.5:
        input_image = tf.image.flip_left_right(input_image)
        real_image = tf.image.flip_left_right(real_image)

    return input_image, real_image

def load_image_train(image_file):
    input_image, real_image = load(image_file)
    input_image, real_image = random_jitter(input_image, real_image)
    input_image, real_image = normalize(input_image, real_image)

    return input_image, real_image

def load_image_test(image_file):
    input_image, real_image = load(image_file)
    input_image, real_image = resize(input_image, real_image,
                                   IMG_HEIGHT, IMG_WIDTH)
    input_image, real_image = normalize(input_image, real_image)

    return input_image, real_image

def load_image_outliers(image_file):
    input_image = load_single(image_file)
    input_image = resize(input_image, input_image,
                                   IMG_HEIGHT, IMG_WIDTH)
    input_image , input_image = normalize(input_image,input_image)

    return input_image

train_dataset = tf.data.Dataset.list_files(PATH+'/train/*.png')
train_dataset = train_dataset.map(load_image_train, num_parallel_calls=tf.data.experimental.AUTOTUNE)
train_dataset = train_dataset.shuffle(BUFFER_SIZE).batch(BATCH_SIZE)

test_dataset = tf.data.Dataset.list_files(PATH+'/val/*.png')
test_dataset = test_dataset.map(load_image_test)
test_dataset = test_dataset.batch(BATCH_SIZE)

gif_dataset = tf.data.Dataset.list_files(PATH+'/gif/*.png')
gif_dataset = gif_dataset.map(load_image_test)
gif_dataset = gif_dataset.batch(BATCH_SIZE)

#outliers_dataset = tf.data.Dataset.list_files(PATH+'/outliers/*.png')
#outliers_dataset = outliers_dataset.map(load_image_outliers)
#outliers_dataset = outliers_dataset.batch(BATCH_SIZE)

generator = buildGenerator()

LAMBDA = 100

def generator_loss(disc_generated_output, gen_output, target):
    gan_loss = loss_object(tf.ones_like(disc_generated_output), disc_generated_output)

    l1_loss = tf.reduce_mean(tf.abs(target - gen_output))

    total_gen_loss = gan_loss + (LAMBDA * l1_loss)

    return total_gen_loss, gan_loss, l1_loss

discriminator = buildDiscriminator()

loss_object = tf.keras.losses.BinaryCrossentropy(from_logits=True)

def discriminator_loss(disc_real_output, disc_generated_output):
    real_loss = loss_object(tf.ones_like(disc_real_output), disc_real_output)

    generated_loss = loss_object(tf.zeros_like(disc_generated_output), disc_generated_output)

    total_disc_loss = real_loss + generated_loss

    return total_disc_loss

generator_optimizer = tf.keras.optimizers.legacy.Adam(2e-4, beta_1=0.5)
discriminator_optimizer = tf.keras.optimizers.legacy.Adam(2e-4, beta_1=0.5)

checkpoint_dir = './training_checkpoints'
checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt")
checkpoint = tf.train.Checkpoint(generator_optimizer=generator_optimizer,
                                 discriminator_optimizer=discriminator_optimizer,
                                 generator=generator,
                                 discriminator=discriminator)

def generate_images(model, test_input, tar, epoch):
    prediction = model(test_input, training=True)
    plt.figure(figsize=(15,15))

    display_list = [test_input[0], tar[0], prediction[0]]
    title = ['Input Image','Ground Truth', 'Predicted Image']

    for i in range(3):
        plt.subplot(1, 3, i+1)
        plt.title(title[i])
        plt.imshow(display_list[i] * 0.5 + 0.5)
        plt.axis('off')
    plt.savefig("progressV2/image_"+str(epoch+6)+".png")
    #plt.show()

import datetime
log_dir="logs/"

summary_writer = tf.summary.create_file_writer(
  log_dir + "fit/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))

@tf.function
def train_step(input_image, target, epoch):
    with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
        gen_output = generator(input_image, training=True)

        disc_real_output = discriminator([input_image, target], training=True)
        disc_generated_output = discriminator([input_image, gen_output], training=True)

        gen_total_loss, gen_gan_loss, gen_l1_loss = generator_loss(disc_generated_output, gen_output, target)
        disc_loss = discriminator_loss(disc_real_output, disc_generated_output)

    generator_gradients = gen_tape.gradient(gen_total_loss,
                                          generator.trainable_variables)
    discriminator_gradients = disc_tape.gradient(disc_loss,
                                               discriminator.trainable_variables)

    generator_optimizer.apply_gradients(zip(generator_gradients,
                                          generator.trainable_variables))
    discriminator_optimizer.apply_gradients(zip(discriminator_gradients,
                                              discriminator.trainable_variables))

    with summary_writer.as_default():
        tf.summary.scalar('gen_total_loss', gen_total_loss, step=epoch)
        tf.summary.scalar('gen_gan_loss', gen_gan_loss, step=epoch)
        tf.summary.scalar('gen_l1_loss', gen_l1_loss, step=epoch)
        tf.summary.scalar('disc_loss', disc_loss, step=epoch)

def fit(train_ds, epochs, test_ds):
    for epoch in range(epochs):
        start = time.time()

        #for example_input, example_target in test_ds.take(1):
        #    generate_images(generator, example_input, example_target)

        generate_images(generator,sample_input,sample_output,epoch)
        print("Epoch: ", epoch)

        for n, (input_image, target) in train_ds.enumerate():
            print('.', end='')
            if (n+1) % 100 == 0:
                print()

            train_step(input_image, target, epoch)
        print()

        if (epoch + 1) % 5 == 0:
            checkpoint.save(file_prefix = checkpoint_prefix)

        print ('Time taken for epoch {} is {} sec\n'.format(epoch + 1,
                                                        time.time()-start))
    checkpoint.save(file_prefix = checkpoint_prefix)

#to take a random image for testing while training
for input , output in gif_dataset.take(1):
    sample_input , sample_output = input , output


checkpoint.restore(tf.train.latest_checkpoint(checkpoint_dir))

fit(train_dataset, EPOCHS, test_dataset)

for example_input, example_target in test_dataset.take(5):
    generate_images(generator, example_input, example_target)

generator.save('AnimeColorizationModelv3.h5')
