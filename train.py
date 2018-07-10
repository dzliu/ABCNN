# coding=utf-8

import datetime
import os
import torch
import torchvision
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from tqdm import tqdm

from utils import save_checkpoint
from utils import generate_plots



# Use GPU if available, otherwise use CPU.
USE_CUDA = torch.cuda.is_available()

def train(model, loss_fn, optimizer, metrics, history, trainset, valset, 
            config):
    """ Trains the model by optimizing with respect to the given loss
        function using the given optimizer.

        Args:
            model: torch.nn.Module 
                Defines the model.
            loss_fn: torch.nn.Module 
                Defines the loss function.
            optimizer: torch.optim.optimizer 
                Defines the optimizer.
            metrics: dict
                Contains callable functions for each metric.
            history: dict
                Contains histories of desired run metrics.
            trainset: torch.utils.data.Dataset 
                Contains the training data.
            valset: a torch.utils.data.Dataset 
                Contains the validation data.
            config: dict
                Configures the training loop. Contains the following keys:

                batch_size: int
                    The number of examples to process per batch.
                    Default value is 64.
                start_epoch: int
                    The epoch to start on for training.
                    Default value is 1.
                num_epochs: int
                    How many epochs to train the model.
                    Default value is 20.
                log_every: int
                    How often to save model checkpoints and generate
                    plots. To turn off logging, set this value to 0.
                    Default value is 5.
                num_workers: int
                    How many works to assign to the DataLoader.
                    Default value is 4.

        Returns:
            model: a torch.nn.Module defining the trained model.
    """

    # Get keyword parameter values
    batch_size = config.get("batch_size", 20)
    start_epoch = config.get("start_epoch", 1)
    num_epochs = config.get("num_epochs", 20)
    log_every = config.get("save_every", 5)
    num_workers = config.get("num_workers", 4)
    checkpoint_dir = config.get("checkpoint_dir", "checkpoints")

    # Training loop
    for epoch in tqdm(range(start_epoch, num_epochs + 1), desc="Epochs", position=0):

        # Process train and val datasets
        model, train_loss = process_batches(model, loss_fn, optimizer, trainset, batch_size, num_workers, True)
        val_loss = process_batches(model, loss_fn, optimizer, valset, batch_size, num_workers, False)

        # Update run statistics
        # TODO: Add tracking for other statistics
        history["train loss"].append(train_loss)
        history["val loss"].append(val_loss)

        # Log results
        if log_every != 0 and epoch % log_every == 0:
            filename = str(datetime.datetime.now()) # use time stamp to name file
            filename = os.path.join(checkpoint_dir, filename)
            save_checkpoint(model, optimizer, history, epoch, filename)
            generate_plots(history)

    return model


def process_batches(model, loss_fn, optimizer, dataset, batch_size, num_workers, is_training):
    """ Processes the examples in the dataset in batches. If the dataset is the
        training set, then the model weights will be updated.

        Args:
            model: torch.nn.Module
                Defines the model.
            loss_fn: torch.nn.Module
                Defines the loss function. The loss function takes batches
                of scores and targets and returns a batch of losses.
            optimizer: torch.optim.optimizer
                Defines the optimizer.
            dataset: torch.utils.data.Dataset
                Contains the examples to process.
            batch_size: int
                The number of examples to process per batch.
            num_workers: int
                How many workers to assign to the DataLoader.
            is_training: boolean
                Specifies whether or not to update model weights.

        Returns:
            model: torch.nn.Module
                The updated model (returned only if is_training is True)
            loss: float
                The loss averaged across the entire dataset.
    """
    # Store batch losses
    total_loss = 0
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    for features, targets in tqdm(dataloader, position=1):

        # Load batch to GPU
        if USE_CUDA:
            torch.cuda.empty_cache()
            features = features.cuda()
            targets = targets.cuda()

        # Forward pass
        scores = model(features)
        batch_loss = torch.sum(loss_fn(scores, targets))
        total_loss += float(batch_loss)

        # Backward pass
        if is_training:
            optimizer.zero_grad()
            batch_loss.backward()
            optimizer.step()     

    # Compute averaged loss
    loss = total_loss / len(dataset)   
    if is_training:
        return model, loss
    else:
        return loss