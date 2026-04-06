pipeline {
  agent any

  environment {
    DATABASE_URL = 'sqlite:///./workspace/jenkins-test.db'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Setup Python') {
      steps {
        bat 'python -m pip install --upgrade pip'
        bat 'pip install -r requirements.txt'
      }
    }

    stage('Run Tests') {
      steps {
        bat 'python automation\\run_tests.py'
      }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: 'automation/reports/**', allowEmptyArchive: true
      junit testResults: 'automation/reports/junit.xml', allowEmptyResults: true
    }
  }
}
