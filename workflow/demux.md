# Demultiplexing

## Flowcells

Flowcells exist in 4 different states:

- **ondisk**: flowcell is present (on the cluster) and FASTQ-files are linked in Housekeeper.
- **removed**: flowcell is _not_ present. When removing a flowcell, the related FASTQ-files are also deleted from Housekeeper identified by the flowcell-name tag. A flowcell is only removed _after_ it's been successfully backed-up.
- **requested**: flowcell is _not_ present but has been marked for retreival from back-up.
- **processing**: flowcell is _not_ present but currently in the process of retreival from back-up or being re-demultiplexed.

Flowcells are automatically set to **requested** when an analysis is automatically started and the system recognises that not all related flowcells are **ondisk**.

    :stopwatch: rasta:~/servers/crontab/analysis-auto.sh
    :man_technologist: cg analysis auto

One person is assigned to retrieve **requested** flowcells. When starting this process, the process should update the status of the flowcell to **processing** in _clinical-api_.

When a flowcell is finished demultiplexing, the flowcell status is automatically updated to **ondisk**. For novel flowcells, a new database record is created with the **ondisk** status. We also update the number of reads each sample on the flowcell has been sequenced. When the target number of reads has been reached, the sample is marked with the sequence date of the latest flowcell for that sample. We also store FASTQ files on a per sample-basis in _Housekeeper_.

    :man_technologist: cg transfer flowcell FLOWCELL-NAME
