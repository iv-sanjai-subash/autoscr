import subprocess
import sys

# Define available AWS accounts and their profiles
AWS_ACCOUNTS = {
    "1": {"name": "Legacy Account", "profile": "audit-readonly"},
    "2": {"name": "Dev Account", "profile": "dev-audit-readonly"},
    "3": {"name": "Management Account", "profile": "management-audit-readonly"},
    "4": {"name": "Production Account", "profile": "production-audit-readonly"},
    "5": {"name": "Shared Services Account", "profile": "shared-services-audit-readonly"},
    "6": {"name": "Staging Account", "profile": "staging-audit-readonly"},
    "7": {"name": "Log Archive Account", "profile": "log-archive-audit-readonly"},
    "8": {"name": "Audit Account", "profile": "audit-audit-readonly"}
}

# Main function
def main():
    while True:
        # Step 1: Choose the AWS Account
        print("\nSelect the AWS Account:")
        print("------------------------")
        for key, account in AWS_ACCOUNTS.items():
            print(f"{key}. {account['name']} ({account['profile']})")
        print("0. Exit")
        account_choice = input("Choose the account: ").strip()

        if account_choice == "0":
            print("Exiting...")
            sys.exit(0)

        if account_choice not in AWS_ACCOUNTS:
            print("Invalid account choice. Please choose a valid option.")
            continue

        # Selected account details
        selected_account = AWS_ACCOUNTS[account_choice]
        profile = selected_account["profile"]
        print(f"\nYou selected: {selected_account['name']} ({profile})")

        # Step 2: Choose the Audit Type
        while True:
            print("\nMaster Audit Menu")
            print("------------------")
            print("1. EC2 Audit")
            print("2. RDS Audit")
            print("3. Security Audit")
            print("4. Monitoring Audit")
            print("5. S3 Audit")
            print("0. Back to Account Selection")
            choice = input("Choose the option to start: ").strip()

            if choice == '1':
                print("Starting EC2 Audit...")
                subprocess.call(["python3", "ec2auditfull.py", profile])
            elif choice == '2':
                print("Starting RDS Audit...")
                subprocess.call(["python3", "rdsaudit.py", profile])
            elif choice == '3':
                print("Starting Security Audit...")
                subprocess.call(["python3", "sgaudit.py", profile])
            elif choice == '4':
                print("Starting Monitoring Audit...")
                subprocess.call(["python3", "cwaudit.py", profile])
            elif choice == '5':
                print("Starting S3 Audit...")
                subprocess.call(["python3", "s3audit.py", profile])
            elif choice == '0':
                print("Returning to Account Selection...")
                break
            else:
                print("Invalid option. Please choose a valid option.")

if __name__ == '__main__':
    main()

