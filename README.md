# s3git-dev

Sync your S3 files from your local git repository with minimal requests, 
reducing update time and cost.

**This project is still under a lot of work.**
The core is there, but the tests will come whenever I have some time to work on them.


## Usage

### Configuration

In your git repository, create `.git/s3config.cfg`, add the following content in it:
```ini
[default]                                                                                                                                                                                                 
S3_ACCESS_KEY_ID = YOUR_AWS_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY = YOUR_AWS_SECRET_ACCESS_KEY
S3_BUCKET_NAME = YOUR_TARGET_BUCKET_NAME
```

Note: you can create a custom configuration for every branch 
by adding a new section with the name of the branch.

You can optionally add another key `S3_UPLOAD_LOCATION`, 
if you want to specify the directory to upload to.

For example, if you want to upload everything under the folder `public`, add:
```ini
S3_UPLOAD_LOCATION = public
```


### Running the synchronization
To launch the synchronization, just run:

```bash
s3git-sync
```

You can specify the branch, tag or revision to synchronize to as well, using:
```bash
s3git-sync BRANCH_OR_REVISION_NAME
```

If you want to fully reupload your files, you can force the upload through:
```bash
s3git-sync -f
```


----

## TL;DR
**.git/s3config.cfg**

```ini
[BRANCH_NAME OR default]                                                                                                                                                                                                 
S3_ACCESS_KEY_ID = AWS_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY = AWS_SECRET_ACCESS_KEY
S3_BUCKET_NAME = TARGET_BUCKET_NAME
S3_UPLOAD_LOCATION = BASE_PATH
```


**s3sync-git**
```
usage: s3sync-git [-h] [-f] [branch]

positional arguments:
  branch      commit, head or branch to sync at

optional arguments:
  -h, --help  show this help message and exit
  -f          forces a whole reupload
```
