''' Use built-in backend AGG to prevent X server error.
    This error happens when work in remote server through ssh '''
import matplotlib;    matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os, glob
import numpy as np
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sar2ice import convert2fullres

idir = '/Volumes/ExFAT2TB/Sentinel1A/odata_FramStrait_TFs/'
nPC = 6     # number of PC
nPC4cluster = 6     # number of PC to use for clustering
nCluster = 15       # number of cluster
tfsID = range(13)

ifiles = sorted(glob.glob(idir + '*_HH_har_norm.npz'))

# load all normalized TFs from input files
joinedTF = []
for ifile in ifiles:
    print ifile
    hhhvTF = []
    for pol in ['HH', 'HV']:
        # load normalized TF from HH or HV as 3D cubes (13 x rows x cols)
        harData = np.load(ifile.replace('_HH_', '_%s_' % pol))['tfsNorm'][tfsID,:,:]
        # join TFs into single 2D matrix (26 x rows*cols)
        hhhvTF.append(harData.reshape(len(tfsID), harData.shape[1]*harData.shape[2]))
    joinedTF.append(np.vstack(hhhvTF))
joinedTF = np.hstack(joinedTF)

ofile = idir + 'joined_'

# select good pixels only
gpi = np.isfinite(joinedTF.sum(axis=0))

# run PCA to reduce dimensionality and keep information
print 'run PCA'
pcaDataGood = PCA(n_components=nPC).fit_transform(joinedTF[:, gpi].T)

# run automatic unsupervised classification using k-means
print 'run KMeans'
lablesGood = KMeans(n_clusters=nCluster).fit_predict(pcaDataGood[:, :nPC4cluster])

# make scatter plots with (1st vs 2nd and 2nd vs 3rd) principal components
# colored by clusters
print 'make scatter plots'
for i in range(nPC-1):
    plt.scatter(pcaDataGood[:,i], pcaDataGood[:,i+1], 1, lablesGood, linewidths=0)
    plt.savefig(ofile + 'scatter%d%d.png' %(i,i+1), dpi=150, bbox_inches='tight', pad_inches=0)
    plt.close('all')

# paste good PC and labels data into full size matrix
pcaDataAll = np.zeros((nPC, joinedTF.shape[1])) + np.nan
pcaDataAll[:, gpi] = pcaDataGood.T
labelsAll = np.zeros(joinedTF.shape[1]) + np.nan
labelsAll[gpi] = lablesGood

# save PCs and labels in input-specific files
pointer = 0
for ifile in ifiles:
    print 'save PCA to', os.path.split(ifile)[1]
    # load sample data just to get the shape of the input grid
    harDataShape = np.load(ifile)['tfsNorm'][tfsID,:,:].shape
    harDataSize = harDataShape[1]*harDataShape[2]
    # fetch PCA and lables for that image values from matrix with all data
    pcaData = pcaDataAll[:, pointer:pointer+harDataSize].reshape(
                  nPC, harDataShape[1], harDataShape[2] )
    labels = labelsAll[pointer:pointer+harDataSize].reshape(
                 harDataShape[1], harDataShape[2] )
    pointer += harDataSize

    # save PCA and labels data
    ofile = ifile.replace('HH_har_norm', 'pca_zones')
    np.savez_compressed(ofile, pcaData=pcaData, labels=labels)

    # vis. spatial distribution of PCAs and labels (map of zones)
    for ipc, pc in enumerate(pcaData):
        vmin, vmax = np.percentile( pc[np.isfinite(pc)], (2.5, 97.5) )
        plt.imsave( ifile.replace('HH_har_norm.npz', 'pc%02d.png' % ipc),
                    pc, vmin=vmin, vmax=vmax )

    # save full-size zones (zoom WS-times)
    labels_ms = np.zeros((labels.shape[0]+1, labels.shape[1]+1)) + np.nan
    labels_ms[:labels.shape[0], :labels.shape[1]] = labels
    fs_dim = np.load(ifile)['proc_params'].item()['input_dimension']
    ws = np.load(ifile)['proc_params'].item()['window_size']
    labels_fs = convert2fullres(labels_ms,fs_dim,ws)
    plt.imsave(ifile.replace('HH_har_norm.npz', 'zones.png'), labels_fs)