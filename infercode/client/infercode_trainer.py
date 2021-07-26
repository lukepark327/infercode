import sys
import os
import pickle
from pathlib import Path
# To import upper level modules
sys.path.append(str(Path('.').absolute().parent))
import logging
from infercode.data_utils.ast_util import ASTUtil
from infercode.data_utils.token_vocab_extractor import TokenVocabExtractor
from infercode.data_utils.subtree_vocab_extractor import SubtreeVocabExtractor
from infercode.data_utils.dataset_processor import DatasetProcessor
from infercode.data_utils.threaded_iterator import ThreadedIterator
from infercode.data_utils.data_loader import DataLoader
from infercode.network.infercode_network import InferCodeModel
from infercode.data_utils.vocabulary import Vocabulary
from infercode.data_utils.language_util import LanguageUtil
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()

class InferCodeTrainer():

    LOGGER = logging.getLogger('InferCodeTrainer')

    def __init__(self, language):
        self.language = language

    def init_from_config(self, config=None):
        # Load default config if do not provide an external one
        if config == None:
            import configparser 
            current_path = os.path.dirname(os.path.realpath(__file__))
            current_path = Path(current_path)
            parent_of_current_path = current_path.parent.absolute()
            config = configparser.ConfigParser()
            default_config_path = os.path.join(parent_of_current_path, "configs/default_config.ini")
            config.read(default_config_path)

        resource_config = config["resource"]
        training_config = config["training_params"]
        nn_config = config["neural_network"]

        self.data_path = resource_config["data_path"]
        self.output_processed_data_path = resource_config["output_processed_data_path"]
        self.node_type_vocab_model_prefix = resource_config["node_type_vocab_model_prefix"]
        self.node_token_vocab_model_prefix = resource_config["node_token_vocab_model_prefix"]
        self.subtree_vocab_model_prefix = resource_config["subtree_vocab_model_prefix"]

        # Training params
        self.epochs = int(training_config["epochs"])
        self.batch_size = int(nn_config["batch_size"])
        self.checkpoint_every = int(training_config["checkpoint_every"])
        self.model_checkpoint = training_config["model_checkpoint"]

        self.language_util = LanguageUtil()
        self.language_index = self.language_util.get_language_index(self.language)

        if not os.path.exists(self.model_checkpoint):
            os.mkdir(model_checkpoint)


        self.data_processor = DatasetProcessor(input_data_path=self.data_path, 
                                               output_tensors_path=self.output_processed_data_path, 
                                               node_token_vocab_model_prefix=self.node_token_vocab_model_prefix, 
                                               subtree_vocab_model_prefix=self.subtree_vocab_model_prefix, 
                                               language=self.language)
        self.training_buckets = self.data_processor.process_or_load_data()



        # self.ast_util, self.training_buckets = self.process_or_load_data()        
        self.data_loader = DataLoader(self.batch_size)

        self.node_type_vocab = Vocabulary(100000, self.node_type_vocab_model_prefix + ".model")
        self.node_token_vocab = Vocabulary(100000, self.node_token_vocab_model_prefix + ".model")
        self.subtree_vocab = Vocabulary(100000, self.subtree_vocab_model_prefix + ".model")

        
        # ------------Set up the neural network------------
        self.infercode_model = InferCodeModel(num_types=self.node_type_vocab.get_vocabulary_size(), 
                                              num_tokens=self.node_token_vocab.get_vocabulary_size(), 
                                              num_subtrees=self.subtree_vocab.get_vocabulary_size(),
                                              num_languages=self.language_util.get_num_languages(),
                                              num_conv=int(nn_config["num_conv"]), 
                                              node_type_dim=int(nn_config["node_type_dim"]), 
                                              node_token_dim=int(nn_config["node_token_dim"]),
                                              conv_output_dim=int(nn_config["conv_output_dim"]), 
                                              include_token=int(nn_config["include_token"]), 
                                              batch_size=int(nn_config["batch_size"]), 
                                              learning_rate=float(nn_config["lr"]))

        self.saver = tf.train.Saver(save_relative_paths=True, max_to_keep=5)
        self.init = tf.global_variables_initializer()
        self.sess = tf.Session()
        self.sess.run(self.init)

        self.checkfile = os.path.join(self.model_checkpoint, 'cnn_tree.ckpt')
        ckpt = tf.train.get_checkpoint_state(self.model_checkpoint)
        if ckpt and ckpt.model_checkpoint_path:
            self.LOGGER.info("Load model successfully : " + str(self.checkfile))
            self.saver.restore(self.sess, ckpt.model_checkpoint_path)
        else:
            self.LOGGER.error("Could not find the model : " + str(self.checkfile))
            self.LOGGER.error("Train the model from scratch")
        
        # -------------------------------------------------

    def train(self):
        for epoch in range(1,  self.epochs + 1):
            train_batch_iterator = ThreadedIterator(self.data_loader.make_minibatch_iterator(self.training_buckets), max_queue_size=5)
            for train_step, train_batch_data in enumerate(train_batch_iterator):
                _, err = self.sess.run(
                    [self.infercode_model.training_point,
                    self.infercode_model.loss],
                    feed_dict={
                        self.infercode_model.placeholders["node_type"]: train_batch_data["batch_node_type_id"],
                        self.infercode_model.placeholders["node_tokens"]:  train_batch_data["batch_node_tokens_id"],
                        self.infercode_model.placeholders["children_index"]:  train_batch_data["batch_children_index"],
                        self.infercode_model.placeholders["children_node_type"]: train_batch_data["batch_children_node_type_id"],
                        self.infercode_model.placeholders["children_node_tokens"]: train_batch_data["batch_children_node_tokens_id"],
                        self.infercode_model.placeholders["labels"]: train_batch_data["batch_subtree_id"],
                        self.infercode_model.placeholders["language_index"]: self.language_index,
                        self.infercode_model.placeholders["dropout_rate"]: 0.4
                    }
                )

                self.LOGGER.info(f"Training at epoch {epoch} and step {train_step} with loss {err}")
                v = train_step % self.checkpoint_every
                if train_step % self.checkpoint_every == 0:
                    self.saver.save(self.sess, self.checkfile)                  
                    self.LOGGER.info(f"Checkpoint saved, epoch {epoch} and step {train_step} with loss {err}")