import { CfnParameter, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as sc from 'aws-cdk-lib/aws-servicecatalog';

export class ScnorthsouthStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const accountId = cdk.Stack.of(this).account;
    const region = cdk.Stack.of(this).region;

    // Context Keys
    // SCEndUser

    // iam policy
    const iamPolicy = new iam.Policy(this, 'iam-policy', {
      statements: [
        new iam.PolicyStatement({
	  actions: [
	    'iam:GetRole',
	    'iam:UntagRole',
	    'iam:TagRole',
	    'iam:CreateRole',
	    'iam:DeleteRole',
	    'iam:AttachRolePolicy',
	    'iam:PutRolePolicy',
	    'iam:TagPolicy',
	    'iam:PassRole',
	    'iam:DetachRolePolicy',
	    'iam:DeleteRolePolicy',
	    'iam:UntagPolicy',
	    'iam:GetRolePolicy'
	  ],
	  effect: iam.Effect.ALLOW,
	  resources: [
	    `arn:aws:iam::${accountId}:policy/*`,
	    `arn:aws:iam::${accountId}:role/*NorthSouthProviderRole`
	  ]
	})
      ]
    });
    // cfn policy
    const cfnPolicy = new iam.Policy(this, 'cfn-policy', {
      statements: [
        new iam.PolicyStatement({
	  actions: [
	    'cloudformation:SetStackPolicy',
	    'cloudformation:DescribeStackResources',
	    'cloudformation:SignalResource',
	    'cloudformation:DescribeStackResource',
	    'cloudformation:GetTemplateSummary',
	    'cloudformation:DescribeStacks',
	    'cloudformation:RollbackStack',
	    'cloudformation:GetStackPolicy',
	    'cloudformation:DescribeStackEvents',
	    'cloudformation:CreateStack',
	    'cloudformation:GetTemplate',
	    'cloudformation:DeleteStack',
	    'cloudformation:TagResource',
	    'cloudformation:UpdateStack',
	    'cloudformation:UntagResource',
	    'cloudformation:ListStackResources'
	  ],
	  effect: iam.Effect.ALLOW,
	  resources: [
	    `arn:aws:cloudformation:${region}:${accountId}:stackset/*`,
	    `arn:aws:cloudformation:${region}:${accountId}:stack/*/*`,
	    `arn:aws:cloudformation:${region}:${accountId}:changeSet/*/*`
	  ]
	}),
	new iam.PolicyStatement({
	  actions: [
	    'cloudformation:RegisterType',
	    'cloudformation:ListStacks',
	    'cloudformation:SetTypeDefaultVersion',
	    'cloudformation:DescribeType',
	    'cloudformation:PublishType',
	    'cloudformation:ListTypes',
	    'cloudformation:DeactivateType',
	    'cloudformation:SetTypeConfiguration',
	    'cloudformation:DeregisterType',
	    'cloudformation:ListTypeRegistrations',
	    'cloudformation:TestType',
	    'cloudformation:ValidateTemplate',
	    'cloudformation:ListTypeVersions'
	  ],
	  effect: iam.Effect.ALLOW,
	  resources: [
	    '*'
	  ]
	})
      ]
    });
    // lambda policy
    const lambdaPolicy = new iam.Policy(this, 'lambda-policy', {
      statements: [
        new iam.PolicyStatement({
	  actions: [
	    'lambda:CreateFunction',
	    'lambda:TagResource',
	    'lambda:InvokeFunction',
	    'lambda:GetFunction',
	    'lambda:InvokeAsync',
	    'lambda:DeleteFunction',
	    'lambda:UntagResource'
	  ],
	  effect: iam.Effect.ALLOW,
	  resources: [
	    `arn:aws:lambda:${region}:${accountId}:function:*NorthSouthProvider`
	  ]
	})
      ]
    });
    // ec2 policy
    const ec2Policy = new iam.Policy(this, 'ec2-policy', {
      statements: [
        new iam.PolicyStatement({
	  actions: [
	    'ec2:DescribeVpcs',
	    'ec2:DescribeSubnets'
	  ],
	  effect: iam.Effect.ALLOW,
	  resources: [
	    '*'
	  ]
	})
      ]
    });
    // scnorthsouth-endusers group
    const scEndUsers = new iam.Group(this, 'sc-northsouth-endusers', {
      groupName: 'sc-northsouth-endusers',
      managedPolicies: [
        iam.ManagedPolicy.fromManagedPolicyArn(this, 'AmazonS3ReadOnlyAccess', 'arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess'),
	iam.ManagedPolicy.fromManagedPolicyArn(this, 'AWSServiceCatalogEndUserFullAccess', 'arn:aws:iam::aws:policy/AWSServiceCatalogEndUserFullAccess')
      ]
    });
    scEndUsers.attachInlinePolicy(ec2Policy);
    scEndUsers.attachInlinePolicy(iamPolicy);
    scEndUsers.attachInlinePolicy(cfnPolicy);
    scEndUsers.attachInlinePolicy(lambdaPolicy);
    // iam user
    const endUser = iam.User.fromUserName(this,'scenduser', this.node.tryGetContext("SCEndUser"));
    scEndUsers.addUser(endUser);
    // portfolio
    const northSouthPortfolio = new sc.Portfolio(this, 'NorthSouthRouteProviderPortfolio', {
      description: 'Portfolio to provision North-South routing',
      displayName: 'North-South Route Provider',
      providerName: 'Network Account Team'
    });
    // product
    const cfTemplateUrl = 'https://sh-network-dev-bucket1.s3.amazonaws.com/northsouth_provider.yaml';
    const northSouthProduct = new sc.CloudFormationProduct(this, 'NorthSouthRouteProviderProduct', {
      productName: 'NorthSouthRouteProvider',
      owner: 'NetworkAdmin',
      productVersions: [
        {
	  productVersionName: 'v1',
	  cloudFormationTemplate: sc.CloudFormationTemplate.fromUrl(cfTemplateUrl)
	}
      ]
    });
    northSouthPortfolio.addProduct(northSouthProduct);
    // access to group
    northSouthPortfolio.giveAccessToGroup(scEndUsers);
  }
}
