import boto3
import botocore
import csv
import sys

def audit_s3_buckets(profile_name):
    # Start the session using the provided AWS profile
    session = boto3.Session(profile_name=profile_name)
    s3_client = session.client('s3')

    # List all S3 buckets
    buckets_response = s3_client.list_buckets()
    buckets = buckets_response.get("Buckets", [])
    total_buckets = len(buckets)

    # Prepare lists for summary information
    access_logging_enabled_buckets = []
    access_logging_disabled_buckets = []
    lifecycle_enabled_buckets = []
    lifecycle_disabled_buckets = []

    # Open CSV file for writing
    with open('s3_audit.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        # Write summary row at the very top: total buckets audited
        writer.writerow([f"Total Buckets Audited: {total_buckets}"])
        # Write CSV header for per-bucket details
        writer.writerow(["Bucket Name", "Storage Class", "Versioning", "Server Access Logging", 
                         "Lifecycle Rule Name", "Lifecycle Rule Status"])

        # Iterate over each bucket
        for bucket in buckets:
            bucket_name = bucket.get("Name", "N/A")
            
            # Set default values for bucket-level settings
            storage_class = "N/A"  # Buckets do not have a bucket-wide storage class.
            versioning_status = "Disabled"
            logging_status = "Disabled"
            lifecycle_rule_name = "Not Configured"
            lifecycle_rule_status = "Not Configured"

            # Fetch versioning status
            try:
                versioning_response = s3_client.get_bucket_versioning(Bucket=bucket_name)
                versioning_status = versioning_response.get("Status", "Disabled")
            except botocore.exceptions.ClientError:
                versioning_status = "Error"

            # Fetch server access logging configuration
            try:
                logging_response = s3_client.get_bucket_logging(Bucket=bucket_name)
                if "LoggingEnabled" in logging_response:
                    logging_status = "Enabled"
                else:
                    logging_status = "Disabled"
            except botocore.exceptions.ClientError:
                logging_status = "Error"

            # Fetch lifecycle configuration and check for an enabled rule
            try:
                lifecycle_response = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                lifecycle_rules = lifecycle_response.get("Rules", [])
                if lifecycle_rules:
                    enabled_rule = None
                    for rule in lifecycle_rules:
                        if rule.get("Status", "Disabled") == "Enabled":
                            enabled_rule = rule
                            break
                    if enabled_rule:
                        lifecycle_rule_name = enabled_rule.get("ID", "Unnamed")
                        lifecycle_rule_status = enabled_rule.get("Status", "Disabled")
                    else:
                        lifecycle_rule_name = lifecycle_rules[0].get("ID", "Unnamed")
                        lifecycle_rule_status = lifecycle_rules[0].get("Status", "Disabled")
                else:
                    lifecycle_rule_name = "Not Configured"
                    lifecycle_rule_status = "Not Configured"
            except botocore.exceptions.ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "NoSuchLifecycleConfiguration":
                    lifecycle_rule_name = "Not Configured"
                    lifecycle_rule_status = "Not Configured"
                else:
                    lifecycle_rule_name = "Error"
                    lifecycle_rule_status = "Error"

            # Write the bucket's details to the CSV file
            writer.writerow([bucket_name, storage_class, versioning_status, logging_status, 
                             lifecycle_rule_name, lifecycle_rule_status])

            # Accumulate bucket names for summary based on logging status
            if logging_status == "Enabled":
                access_logging_enabled_buckets.append(bucket_name)
            else:
                access_logging_disabled_buckets.append(bucket_name)

            # Accumulate bucket names for lifecycle configuration: treat only those with status "Enabled" as enabled
            if lifecycle_rule_status == "Enabled":
                lifecycle_enabled_buckets.append(bucket_name)
            else:
                lifecycle_disabled_buckets.append(bucket_name)

        # Append additional summary rows at the end of the CSV output.
        writer.writerow([])  # Blank line for readability
        writer.writerow(["Buckets Enabled for Access Logging", "Buckets Disabled for Access Logging"])
        writer.writerow([", ".join(access_logging_enabled_buckets), ", ".join(access_logging_disabled_buckets)])
        writer.writerow([])  # Blank line for readability
        writer.writerow(["Buckets with Lifecycle Setup Enabled", "Buckets with Lifecycle Setup Disabled"])
        writer.writerow([", ".join(lifecycle_enabled_buckets), ", ".join(lifecycle_disabled_buckets)])

    print("S3 bucket audit completed. Output saved to s3_audit.csv")

if __name__ == "__main__":
    # Accept the AWS profile as a command-line argument.
    if len(sys.argv) != 2:
        print("Usage: python3 s3audit.py <AWS_PROFILE>")
        sys.exit(1)

    PROFILE_NAME = sys.argv[1]
    try:
        audit_s3_buckets(PROFILE_NAME)
    except botocore.exceptions.NoCredentialsError:
        print("No credentials found. Please ensure your profile is set up correctly in .aws/config.")

