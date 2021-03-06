# coding=utf-8

import argparse
import os
import torch
import torch.nn as nn
import torch.optim as optim
from collections import defaultdict

from setup import read_config
from setup import setup_v2
from train import train
from train import evaluate
from utils import load_checkpoint
from utils import freeze_weights

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--config", default="config.json", help="path to the config file")
parser.add_argument("--train", action="store_true", default=False, help="train a model")
parser.add_argument("--eval", action="store_true", default=False, help="evaluate a model")
parser.add_argument("--path", default=None, help="path to model checkpoint")
parser.add_argument("--freeze", action="store_true", default=False, help="freeze the weights in the conv-pool layers.")
args = parser.parse_args()

# Sanity check command line arguments
assert(args.train or args.eval)

# Basic setup
config = read_config(args.config)
datasets, model = setup_v2(config)
loss_fn = nn.CrossEntropyLoss()
optimizer = \
    optim.Adagrad(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=config["optim"]["lr"],
        weight_decay=config["optim"]["weight_decay"]
    )
history = defaultdict(list)

# Load trained model if specified
if args.path is not None:
    print("Loading model from checkpoint...")
    state = load_checkpoint(args.path)
    model_dict, optim_dict, history, epoch = state
    model.load_state_dict(model_dict)
    optimizer.load_state_dict(optim_dict)
    config["train"]["start_epoch"] = epoch
    print("Success!")

if args.freeze:
    print("Freezing weights of pre-trained model...")
    model = freeze_weights(model)

if args.train:
    print("Training the model...")
    trainset = datasets[config["train_set"]]
    valset = datasets[config["val_set"]]
    train_config = config["train"]
    train(model, loss_fn, optimizer, history, trainset, valset, train_config)

elif args.eval:
    print("Evaluating the model...")
    testset = datasets[config["test_set"]]
    batch_size = config["train"]["batch_size"]
    num_workers = config["train"]["num_workers"]
    evaluate(model, testset, loss_fn, batch_size, num_workers)
