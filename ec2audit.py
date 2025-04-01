import boto3
import botocore

def list_ec2_instances(profile_name):
    session = boto3.Session(profile_name=profile_name)
    ec2_client = session.client('ec2')

    # List all EC2 instances
    print("Listing EC2 instances:")
    instances = ec2_client.describe_instances()
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            platform = instance.get('Platform', 'Linux')  # Default to Linux if 'Platform' is not present
            volumes = [block['Ebs']['VolumeId'] for block in instance.get('BlockDeviceMappings', [])]
            instance_name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), "N/A")
            print(f"Instance Name: {instance_name}, ID: {instance_id}, Platform: {platform}, Attached Volumes: {volumes}")
    
    # List all AMIs
    print("\nListing AMIs:")
    images = ec2_client.describe_images(Owners=['self'])
    for image in images['Images']:
        ami_id = image['ImageId']
        instance_name = image.get('Name', "N/A")
        print(f"AMI ID: {ami_id}, Instance Name: {instance_name}")

    # List all EBS volumes
    print("\nListing EBS Volumes:")
    volumes = ec2_client.describe_volumes()
    for volume in volumes['Volumes']:
        volume_id = volume['VolumeId']
        tags = {tag['Key']: tag['Value'] for tag in volume.get('Tags', [])}
        backup_status = tags.get('backup', "No Backup Tag")
        attached_instance = next((attachment['InstanceId'] for attachment in volume.get('Attachments', [])), "Not Attached")
        attached_instance_name = next((tags['Name'] for tags in volume.get('Tags', []) if tags.get('Key') == 'Name'), "N/A")
        print(f"Volume ID: {volume_id}, Attached Instance: {attached_instance}, Backup Status: {backup_status}, Attached Instance Name: {attached_instance_name}")

if __name__ == "__main__":
    PROFILE_NAME = "audit-readonly"  # Replace with your profile name in .aws/config
    try:
        list_ec2_instances(PROFILE_NAME)
    except botocore.exceptions.NoCredentialsError:
        print("No credentials found. Please ensure your profile is set up correctly in .aws/config.")

