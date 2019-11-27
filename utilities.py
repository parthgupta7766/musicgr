import os
import glob

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from librosa.feature import melspectrogram
from librosa import power_to_db, load
from librosa.display import specshow

from tensorflow.keras.utils import Sequence 

def view_melspec(source, sr):
    plt.figure(figsize=(10, 4))
    S = melspectrogram(source, sr=sr)
    S_dB = power_to_db(S, ref=np.max)
    specshow(S_dB, x_axis='time',
                             y_axis='mel', sr=sr,
                             fmax=8000)
    plt.colorbar(format='%+2.0f dB')
    plt.title('Mel-frequency spectrogram')
    plt.tight_layout()
    plt.show()

def id_from_path(mp3_path):
    """
    returns the id of the given mp3 path.
    """
    return os.path.split(mp3_path)[1][:-4]

def attach_onehot_encoding(df, column_name):
    """
    Append the onehot representation of `column` onto the right end
    of the array df.
    """

    df = pd.concat([df, pd.get_dummies(df.genre)], axis=1)

    return df

def mp3_to_mel_path(mp3_path, melspec_dir):
    """
    Take the mp3 path and find the melspec path.
    Returns the melspec path.
    """

    melspec_path = os.path.join(melspec_dir, id_from_path(mp3_path) + ".npz")

    if os.path.exists(melspec_path):
        return melspec_path
    else:
        raise FileNotFoundError(
            f"Did not find a melspectrogram with id {id_from_path(mp3_path)}"
        )

def read_metadata_file(path, all_filepaths, bad_filepaths):
    all_metadata = pd.read_csv(path, header=[0,1], index_col=0)
    
    cols_to_keep = [('track', 'genre_top')]

    # This will be the main dataframe for here on out:
    df = all_metadata.loc[
                all_metadata[('set', 'subset')] == 'small',
                cols_to_keep
    ]

    df.reset_index(inplace=True)
    
    df.columns = ['track_id', 'genre']
    
    # add filepaths to the dataframe
    df['mp3_path'] = all_filepaths
    
    # Remove bad mp3s from the dataframe so that we skip them.
    if df.mp3_path.isin(bad_filepaths).sum():
        df.drop(
            df.loc[df.mp3_path.isin(bad_filepaths), :].index,
            inplace=True
        )
        print(f"Dropped {len(bad_filepaths)} rows from the dataframe.")

    return df


class Batch_generator(Sequence) :
    """
    Data generator class. Takes in the meta dataframe (or a train/test/split) 
    and peels off the paths and the encoded genres.
    """
  
    def __init__(self, meta_df, batch_size, sr, duration):
        self.mp3_paths = meta_df['mp3_path'].to_list()
        self.labels = meta_df.loc[:, meta_df.genre.unique()].to_numpy()
        self.batch_size = batch_size
        self.sr = sr
        self.duration = duration
    
    def __len__(self):
        """
        Return number of batches.
        """
        return (np.ceil(len(self.mp3_paths) / float(self.batch_size))).astype(np.int)
  
    def __getitem__(self, idx):
        
        batch_x = self.mp3_paths[idx * self.batch_size : (idx + 1) * self.batch_size]
        batch_y = self.labels[idx * self.batch_size : (idx + 1) * self.batch_size, :]
        
        return self._stack_melspecs(batch_x), batch_y
    
    def _stack_melspecs(self, filepath_list):
        """
        A helper function for loading batches of melspectrograms.
        Stack the melspectrograms of the files in the list.
        Extends by zeros if needed.
        """
        sources = [load(file, sr=self.sr, duration=self.sr)[0] for file in filepath_list]

        melspecs = [melspectrogram(src, sr=self.sr) for src in sources]
        
        
        stacked_arr = np.zeros((len(filepath_list),
                                max(
                                    [melspec.shape[0] for melspec in melspecs]
                                ),
                                max(
                                    [melspec.shape[1] for melspec in melspecs]
                                )
                               )
                              )

        for i in range(len(filepath_list)):
            stacked_arr[i,
                    :melspecs[i].shape[0],
                    :melspecs[i].shape[1]] = melspecs[i]
        
        return stacked_arr

