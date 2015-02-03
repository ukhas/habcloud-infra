# Amazon Web Services Setup

HabCloud currently uses AWS for storing backups.

We create IAM users for each host, which have permission via a Group policy to 
upload only to their own bucket, which are named with the hostnames. Each 
bucket has a lifecycle configuration that causes uploads to be immediately 
transitioned to Glacier storage, and deleted permanently after one year.

Each backup job, defined in a Salt state, specifies a command to run and a user 
to run it as. This command's stdout is then gzipped, GPG encrypted to the 
HabCloud backups public key, and uploaded to S3.

Recovery is currently a manual operation: only the system administrators have 
either access credentials for AWS sufficient to download objects or the private 
GPG key necessary to decrypt them.

## Configuring AWS

We create a user `manage-backups` which has the following policy applied:

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:PutLifecycleConfiguration"
      ],
      "Resource": [
        "arn:aws:s3:::*.vm.habhub.org"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListAllMyBuckets"
      ],
      "Resource": [
        "arn:aws:s3:::*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateAccessKey",
        "iam:CreateUser"
      ],
      "Resource": [
        "arn:aws:iam::ACCOUNT_ID:user/*.vm.habhub.org"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:ListUsers"
      ],
      "Resource": [
        "arn:aws:iam::ACCOUNT_ID:user/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:AddUserToGroup"
      ],
      "Resource": [
        "arn:aws:iam::ACCOUNT_ID:user/*.vm.habhub.org",
        "arn:aws:iam::ACCOUNT_ID:group/habcloud-backups"
      ]
    }
  ]
}
```

Note you must replace ACCOUNT_ID above with your AWS account ID.

This policy allows it to create buckets and configure their lifecycle in the 
`*.vm.habhub.org` namespace and to list all buckets on the account. It allows 
the account to create new users and give them access keys in the 
`*.vm.habhub.org` namespace, add those users to the `habcloud-backups` group, 
and list all users on the account.

We create a group `habcloud-backups` with the following policy:

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::${aws:username}/*"
      ]
    }
  ]
}
```

This policy allows users in the group to upload objects to the S3 bucket named 
after them (and no other bucket).

## Admin Usage

Backup buckets and user accounts are managed via the `habcloud-vms` script, 
which can list current users and buckets (`list-backups`) and create new 
user/bucket combinations (`create-backup`). With the `--pillar` option to 
`create-backup`, a suitable file for moving to the Salt Pillar is created to 
specify that host's AWS access credentials.

To run the script you must specify the credentials for the `manage-backups` 
user, either by creating `~/.boto`:

```
[Credentials]
aws_access_key_id = ACCESS_KEY
aws_secret_access_key = SECRET_KEY
```

or by specifying environment variables `AWS_ACCESS_KEY_ID` and 
`AWS_SECRET_ACCESS_KEY`.
See the [Boto docs](http://docs.pythonboto.org/en/latest/boto_config_tut.html) 
for more details.
