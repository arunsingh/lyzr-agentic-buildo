# AOB Platform Infrastructure as Code
# Terraform configuration for development, staging, and production environments

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

# Variables
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "aob-platform"
}

variable "node_groups" {
  description = "EKS node groups configuration"
  type = map(object({
    instance_types = list(string)
    min_size      = number
    max_size      = number
    desired_size  = number
    disk_size     = number
  }))
  default = {
    general = {
      instance_types = ["t3.medium", "t3.large"]
      min_size      = 2
      max_size      = 10
      desired_size  = 3
      disk_size     = 50
    }
    compute = {
      instance_types = ["c5.large", "c5.xlarge"]
      min_size      = 1
      max_size      = 5
      desired_size  = 2
      disk_size     = 100
    }
    gpu = {
      instance_types = ["g4dn.xlarge", "g4dn.2xlarge"]
      min_size      = 0
      max_size      = 3
      desired_size  = 1
      disk_size     = 200
    }
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b", "us-west-2c"]
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local values
locals {
  name_prefix = "${var.cluster_name}-${var.environment}"
  common_tags = {
    Environment = var.environment
    Project     = "AOB Platform"
    ManagedBy   = "Terraform"
    Owner       = "Platform Team"
  }
}

# VPC Module
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${local.name_prefix}-vpc"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets = [for i, az in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, i)]
  public_subnets  = [for i, az in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, i + 10)]
  database_subnets = [for i, az in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, i + 20)]

  enable_nat_gateway = true
  enable_vpn_gateway = var.environment == "prod" ? true : false
  enable_dns_hostnames = true
  enable_dns_support   = true

  # VPC Flow Logs
  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_cloudwatch_iam_role  = true
  flow_log_max_aggregation_interval    = 60

  tags = local.common_tags
}

# EKS Cluster Module
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "${local.name_prefix}-cluster"
  cluster_version = "1.28"

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  cluster_endpoint_public_access = var.environment == "prod" ? false : true
  cluster_endpoint_private_access = true

  # EKS Managed Node Groups
  eks_managed_node_groups = {
    for name, config in var.node_groups : name => {
      name = "${local.name_prefix}-${name}"

      instance_types = config.instance_types
      min_size      = config.min_size
      max_size      = config.max_size
      desired_size  = config.desired_size
      disk_size     = config.disk_size

      # Launch template
      launch_template_name        = "${local.name_prefix}-${name}-lt"
      launch_template_description = "Launch template for ${name} node group"
      launch_template_version     = "$Latest"

      # IAM role
      iam_role_name = "${local.name_prefix}-${name}-role"

      # Labels
      labels = {
        node-group = name
        environment = var.environment
      }

      # Taints for GPU nodes
      taints = name == "gpu" ? [{
        key    = "nvidia.com/gpu"
        value  = "true"
        effect = "NO_SCHEDULE"
      }] : []

      tags = local.common_tags
    }
  }

  # Cluster access entry
  manage_aws_auth_configmap = true
  aws_auth_roles = [
    {
      rolearn  = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.name_prefix}-admin"
      username = "admin"
      groups   = ["system:masters"]
    }
  ]

  # Cluster encryption
  cluster_encryption_config = {
    provider_key_arn = aws_kms_key.eks.arn
    resources        = ["secrets"]
  }

  tags = local.common_tags
}

# KMS Key for EKS encryption
resource "aws_kms_key" "eks" {
  description             = "EKS Secret Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation    = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-eks-key"
  })
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${local.name_prefix}-eks"
  target_key_id = aws_kms_key.eks.key_id
}

# RDS Database
module "rds" {
  source = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "${local.name_prefix}-postgres"

  engine               = "postgres"
  engine_version       = "15.4"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = var.environment == "prod" ? "db.r6g.xlarge" : "db.t3.medium"

  allocated_storage     = var.environment == "prod" ? 1000 : 100
  max_allocated_storage = var.environment == "prod" ? 2000 : 200
  storage_encrypted     = true
  kms_key_id           = aws_kms_key.rds.arn

  db_name  = "aob_platform"
  username = "aob_admin"
  password = random_password.db_password.result
  port     = 5432

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = module.vpc.database_subnet_group_name

  backup_retention_period = var.environment == "prod" ? 30 : 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  skip_final_snapshot = var.environment == "dev" ? true : false
  deletion_protection = var.environment == "prod" ? true : false

  performance_insights_enabled = true
  performance_insights_retention_period = var.environment == "prod" ? 7 : 3

  tags = local.common_tags
}

# KMS Key for RDS encryption
resource "aws_kms_key" "rds" {
  description             = "RDS Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-rds-key"
  })
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${local.name_prefix}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

# RDS Security Group
resource "aws_security_group" "rds" {
  name_prefix = "${local.name_prefix}-rds-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-rds-sg"
  })
}

# ElastiCache Redis
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name_prefix}-redis-subnet-group"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${local.name_prefix}-redis"
  description                = "Redis cluster for AOB Platform"

  node_type                  = var.environment == "prod" ? "cache.r6g.large" : "cache.t3.micro"
  port                       = 6379
  parameter_group_name       = "default.redis7"

  num_cache_clusters         = var.environment == "prod" ? 3 : 2
  automatic_failover_enabled = var.environment == "prod" ? true : false
  multi_az_enabled          = var.environment == "prod" ? true : false

  subnet_group_name = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  tags = local.common_tags
}

# Redis Security Group
resource "aws_security_group" "redis" {
  name_prefix = "${local.name_prefix}-redis-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis-sg"
  })
}

# MSK Kafka Cluster
resource "aws_msk_cluster" "kafka" {
  cluster_name           = "${local.name_prefix}-kafka"
  kafka_version          = "3.5.1"
  number_of_broker_nodes = var.environment == "prod" ? 6 : 3

  broker_node_group_info {
    instance_type   = var.environment == "prod" ? "kafka.m5.xlarge" : "kafka.t3.small"
    ebs_volume_size = var.environment == "prod" ? 1000 : 100
    client_subnets  = module.vpc.private_subnets
    security_groups = [aws_security_group.kafka.id]

    storage_info {
      ebs_storage_info {
        volume_size = var.environment == "prod" ? 1000 : 100
      }
    }
  }

  encryption_info {
    encryption_at_rest_kms_key_id = aws_kms_key.kafka.arn
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.kafka.name
      }
    }
  }

  tags = local.common_tags
}

# Kafka Security Group
resource "aws_security_group" "kafka" {
  name_prefix = "${local.name_prefix}-kafka-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 9092
    to_port     = 9092
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }

  ingress {
    from_port   = 9094
    to_port     = 9094
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-kafka-sg"
  })
}

# KMS Key for Kafka encryption
resource "aws_kms_key" "kafka" {
  description             = "Kafka Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-kafka-key"
  })
}

resource "aws_kms_alias" "kafka" {
  name          = "alias/${local.name_prefix}-kafka"
  target_key_id = aws_kms_key.kafka.key_id
}

# CloudWatch Log Group for Kafka
resource "aws_cloudwatch_log_group" "kafka" {
  name              = "/aws/msk/${local.name_prefix}-kafka"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = local.common_tags
}

# S3 Bucket for application data
resource "aws_s3_bucket" "app_data" {
  bucket = "${local.name_prefix}-app-data-${random_string.bucket_suffix.result}"

  tags = local.common_tags
}

resource "aws_s3_bucket_versioning" "app_data" {
  bucket = aws_s3_bucket.app_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "app_data" {
  bucket = aws_s3_bucket.app_data.id

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = aws_kms_key.s3.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "app_data" {
  bucket = aws_s3_bucket.app_data.id

  rule {
    id     = "lifecycle"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# KMS Key for S3 encryption
resource "aws_kms_key" "s3" {
  description             = "S3 Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-s3-key"
  })
}

resource "aws_kms_alias" "s3" {
  name          = "alias/${local.name_prefix}-s3"
  target_key_id = aws_kms_key.s3.key_id
}

# Random password for database
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Random string for S3 bucket suffix
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Outputs
output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = module.eks.cluster_security_group_id
}

output "database_endpoint" {
  description = "RDS database endpoint"
  value       = module.rds.db_instance_endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "kafka_bootstrap_brokers" {
  description = "MSK Kafka bootstrap brokers"
  value       = aws_msk_cluster.kafka.bootstrap_brokers
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3 bucket name for application data"
  value       = aws_s3_bucket.app_data.bucket
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}
