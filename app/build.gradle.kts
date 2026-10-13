plugins {
    id("com.android.application")
}

android {
    namespace = "tj.school.tests"
    compileSdk = 35

    defaultConfig {
        applicationId = "tj.school.tests"
        minSdk = 21
        targetSdk = 35
        versionCode = 2
        versionName = "1.1"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            // Подписываем debug-ключом, чтобы release-APK можно было сразу установить.
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
