import boto3

def fetch_snapshot_counts(profile_name):
    # Use the specified AWS profile
    session = boto3.Session(profile_name=profile_name)
    ec2 = session.client('ec2')

    # Fetch AMIs created by AWS Backup
    amis = ec2.describe_images(Owners=['self'])['Images']
    awsbackup_amis = [ami['ImageId'] for ami in amis if 'awsbackup' in ami.get('Name', '').lower()]

    # Fetch all snapshots
    snapshots = ec2.describe_snapshots(OwnerIds=['self'])['Snapshots']

    # Separate snapshots into counts
    attached_count = 0
    unattached_count = 0

    for snapshot in snapshots:
        snapshot_id = snapshot['SnapshotId']
        # Check if the snapshot is attached to any AWS Backup AMI
        is_attached = False
        for ami in amis:
            if ami['ImageId'] in awsbackup_amis:
                for block_device in ami.get('BlockDeviceMappings', []):
                    # Safely check if 'Ebs' exists in the block device
                    if 'Ebs' in block_device and block_device['Ebs']['SnapshotId'] == snapshot_id:
                        is_attached = True
                        break
            if is_attached:
                break

        if is_attached:
            attached_count += 1
        else:
            unattached_count += 1

    total_snapshots = attached_count + unattached_count
    return attached_count, unattached_count, total_snapshots

def main():
    profile_name = input("Enter your AWS profile name: ")
    try:
        attached_count, unattached_count, total_snapshots = fetch_snapshot_counts(profile_name)
        print(f"\nNumber of snapshots attached to AWS Backup AMIs: {attached_count}")
        print(f"Number of snapshots not matching any AMIs: {unattached_count}")
        print(f"Total number of snapshots: {total_snapshots}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

