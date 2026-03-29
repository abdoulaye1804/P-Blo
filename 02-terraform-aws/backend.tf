terraform {
  backend "s3" {
    bucket         = "finops-autopilot-tfstate"
    key            = "aws/terraform.tfstate"
    region         = "eu-west-1"
    encrypt        = true
    dynamodb_table = "finops-autopilot-tflock"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }

  required_version = ">= 1.6.0"
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "finops-autopilot"
      ManagedBy   = "terraform"
      Environment = var.environment
    }
  }
}
