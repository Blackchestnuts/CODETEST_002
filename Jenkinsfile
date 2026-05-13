pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', credentialsId: 'github-token', url: 'https://github.com/Blackchestnuts/CODETEST_002.git'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'python3 -m pip install --break-system-packages -r requirements.txt'
            }
        }

        stage('Run API Tests') {
            steps {
                sh 'python3 main.py'
            }
        }

        stage('Generate Allure Report') {
            steps {
                sh 'allure generate ./Outputs/allure_report -o ./Outputs/allure_html --clean 2>/dev/null || true'
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'Outputs/**', allowEmptyArchive: true
        }
    }
}
