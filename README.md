# CDK TypeScript project - STNO - North-South Network Route Provider - AWS Service Catalog Product

This is an automation project using CDK development with TypeScript.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

## Purpose

Setup Service Catalog Portfolio, Product for provisioning North-South network routing in a Network Hub Account where STNO is setup.

- Creates a Service Catalog Portfolio
- Creates a Service Catalog Product
- This Service Catalog product can be provisioned once a Member Account's Transit Gateway Attachment is processed by STNO
- On provisioning, the EC2 instances launched in Member Account's VPC (associated with Network Hub) will have:
  - Outbound Network connectivity to Internet
    - *Typical use case is to download OS updates etc.*
  - Inbound Networt connectivity from Network Hub VPC (*a.k.a Security VPC*)

## Setup
- Access to this Service Catalog Portfolio is granted access to End Users / IAM Group: *sc-northsouth-endusers*
- Default End User Id: **scenduser**

> To change default End User Id, update `cdk.json`

## Resouces Configured
- Service Catalog Portfolio
- Service Catalog Product
- IAM policy for IAM actions
- IAM policy for Lambda actions
- IAM policy for CloudFormation actions
- IAM policy for ec2 actions

## Dependencies
- Upload src\northsouth_provider.yaml to S3 Bucket
- Upload src\northsouth_provider.zip to S3 Bucket

## Prerequisite tasks
- Before provisioning Service Catalog Product, following tasks need to be performed
- Provision IPAM Pool for Member Account Region
- Create VPC in Member Account Region using IPAM Pool
- Complete STNO tasks to establish connectivity between Network Hub Account Transit Gateway and Member Account VPC
- Ensure STNO processing is complete

## Provisioning Service Catalog Product
- Login to Network Account as `scenduser`
- In Service Catalog console, select the product
- Click 'Actions' -> 'Launch Product'
- Enter values for:
  - Member Account Id
  - Member Account Region
  - Member VPC Id
  - Member VPC CIDR
- Select:
  - Network Hub Account VPC (Security VPC)
  - Network Hub Account Subnet (Security VPC Subnet)
- Enter Network Hub Account Transit Gateway Id

> - To verify progress of Provisioning operation, login to SharedNetwork AWS Console as `administrator`
> - For each provisioned product, a CloudWatch Log Group is created with name pattern /aws/lambda/AccountId-NorthSouthProvider

### Result
- Product is provisioned
- Network Hub Account Security VPC public route table is updated with route for Member Account VPC CIDR
  - Allow Inbound connectivity between Network Hub Account and Member Account VPC
- Network Hub Account Transit Gateway Route table *Egress-RTB* is updated with route for Member Account VPC CIDR
  - Allow Outbound connectivity

## Deprovisioning Service Catalog Product
- Login to SharedNetwork AWS Console as `scenduser`
- In Service Catalog console, select the `Provisioned Product`
- Click 'Actions' -> 'Terminate'

### Result
- Route corresponding to Member Account VPC will be deleted from Network Hub Account Security VPC
- Route corresponding to Member Account VPC will be deleted from Network Hub Account Transit Gateway Route table *Egress-RTB*
- Provisioned product will be deleted

## Useful commands

* `npm install`     downloads dependencies
* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `cdk deploy`      deploy this stack to your default AWS account/region
* `cdk diff`        compare deployed stack with current state
* `cdk synth`       emits the synthesized CloudFormation template
