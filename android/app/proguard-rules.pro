-dontwarn com.gemalto.jp2.**
-dontwarn com.tom_roush.pdfbox.filter.JPXFilter

# package:jni resolves these Kotlin coroutine types and members by their JVM
# names. Pigeon JNI plugins (including shared_preferences_android) also include
# Continuation in method descriptors, so renaming it breaks release startup.
-keep interface kotlin.coroutines.Continuation { *; }
-keep class kotlin.coroutines.intrinsics.CoroutineSingletons { *; }
-keep class kotlin.coroutines.intrinsics.IntrinsicsKt* { *; }
-keep class kotlin.Result { *; }
-keep class kotlin.Result$Failure { *; }
-keep class kotlin.Unit { *; }
