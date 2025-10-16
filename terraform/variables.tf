# Terraform Variables for AOB Platform

# Environment Configuration
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

# Network Configuration
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

# EKS Node Groups Configuration
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

# Database Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

variable "db_max_allocated_storage" {
  description = "RDS max allocated storage in GB"
  type        = number
  default     = 200
}

variable "db_backup_retention_period" {
  description = "RDS backup retention period in days"
  type        = number
  default     = 7
}

# Redis Configuration
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_clusters" {
  description = "Number of Redis cache clusters"
  type        = number
  default     = 2
}

# Kafka Configuration
variable "kafka_instance_type" {
  description = "MSK Kafka instance type"
  type        = string
  default     = "kafka.t3.small"
}

variable "kafka_number_of_broker_nodes" {
  description = "Number of Kafka broker nodes"
  type        = number
  default     = 3
}

variable "kafka_ebs_volume_size" {
  description = "Kafka EBS volume size in GB"
  type        = number
  default     = 100
}

# Monitoring Configuration
variable "enable_monitoring" {
  description = "Enable CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

# Security Configuration
variable "enable_deletion_protection" {
  description = "Enable deletion protection for critical resources"
  type        = bool
  default     = false
}

variable "enable_encryption" {
  description = "Enable encryption for all resources"
  type        = bool
  default     = true
}

# Cost Optimization
variable "enable_spot_instances" {
  description = "Enable spot instances for non-critical workloads"
  type        = bool
  default     = false
}

variable "enable_scheduled_scaling" {
  description = "Enable scheduled scaling for cost optimization"
  type        = bool
  default     = false
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "project_name" {
  description = "Project name for tagging"
  type        = string
  default     = "AOB Platform"
}

variable "owner" {
  description = "Owner for tagging"
  type        = string
  default     = "Platform Team"
}

variable "cost_center" {
  description = "Cost center for tagging"
  type        = string
  default     = "Engineering"
}

# Environment-specific overrides
locals {
  # Environment-specific configurations
  environment_config = {
    dev = {
      cluster_endpoint_public_access = true
      enable_deletion_protection     = false
      enable_monitoring             = true
      log_retention_days            = 3
      db_backup_retention_period    = 1
      redis_num_cache_clusters      = 1
      kafka_number_of_broker_nodes  = 1
      node_groups = {
        general = {
          instance_types = ["t3.small", "t3.medium"]
          min_size      = 1
          max_size      = 5
          desired_size  = 2
          disk_size     = 20
        }
        compute = {
          instance_types = ["t3.medium"]
          min_size      = 0
          max_size      = 2
          desired_size  = 1
          disk_size     = 50
        }
        gpu = {
          instance_types = ["g4dn.xlarge"]
          min_size      = 0
          max_size      = 1
          desired_size  = 0
          disk_size     = 100
        }
      }
    }
    staging = {
      cluster_endpoint_public_access = true
      enable_deletion_protection     = false
      enable_monitoring             = true
      log_retention_days            = 7
      db_backup_retention_period    = 7
      redis_num_cache_clusters      = 2
      kafka_number_of_broker_nodes  = 3
      node_groups = {
        general = {
          instance_types = ["t3.medium", "t3.large"]
          min_size      = 2
          max_size      = 8
          desired_size  = 3
          disk_size     = 50
        }
        compute = {
          instance_types = ["c5.large"]
          min_size      = 1
          max_size      = 4
          desired_size  = 2
          disk_size     = 100
        }
        gpu = {
          instance_types = ["g4dn.xlarge"]
          min_size      = 0
          max_size      = 2
          desired_size  = 1
          disk_size     = 200
        }
      }
    }
    prod = {
      cluster_endpoint_public_access = false
      enable_deletion_protection     = true
      enable_monitoring             = true
      log_retention_days            = 30
      db_backup_retention_period    = 30
      redis_num_cache_clusters      = 3
      kafka_number_of_broker_nodes  = 6
      node_groups = {
        general = {
          instance_types = ["t3.large", "t3.xlarge"]
          min_size      = 3
          max_size      = 15
          desired_size  = 5
          disk_size     = 100
        }
        compute = {
          instance_types = ["c5.large", "c5.xlarge"]
          min_size      = 2
          max_size      = 8
          desired_size  = 3
          disk_size     = 200
        }
        gpu = {
          instance_types = ["g4dn.xlarge", "g4dn.2xlarge"]
          min_size      = 1
          max_size      = 5
          desired_size  = 2
          disk_size     = 500
        }
      }
    }
  }

  # Current environment configuration
  current_config = local.environment_config[var.environment]
}
