#import <Foundation/Foundation.h>
#import <VideoToolbox/VideoToolbox.h>
#include <signal.h>
#include <unistd.h>
#include <stdatomic.h>

static _Atomic unsigned completed, failures;
static void expired(int sig) { _exit(124); }
static void output(void *ctx, void *frame, OSStatus status,
                   VTEncodeInfoFlags flags, CMSampleBufferRef sample) {
    if (status || !sample) atomic_fetch_add(&failures, 1);
    else atomic_fetch_add(&completed, 1);
}
int main(int argc, char **argv) {
    @autoreleasepool {
        setbuf(stdout, NULL);
        if (argc != 2 || (strcmp(argv[1], "h264-software") &&
                         strcmp(argv[1], "h264-hardware") &&
                         strcmp(argv[1], "hevc-hardware"))) {
            fprintf(stderr, "usage: vt-encode-probe h264-software|h264-hardware|hevc-hardware\n");
            return 2;
        }
        signal(SIGALRM, expired); alarm(45);
        bool hardware = strcmp(argv[1], "h264-software") != 0;
        CMVideoCodecType codec = !strcmp(argv[1], "hevc-hardware") ? kCMVideoCodecType_HEVC : kCMVideoCodecType_H264;
        NSDictionary *spec = hardware
          ? @{(__bridge NSString *)kVTVideoEncoderSpecification_RequireHardwareAcceleratedVideoEncoder:@YES}
          : @{(__bridge NSString *)kVTVideoEncoderSpecification_EnableHardwareAcceleratedVideoEncoder:@NO};
        NSDictionary *attrs = @{
            (__bridge NSString *)kCVPixelBufferPixelFormatTypeKey:@(kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange),
            (__bridge NSString *)kCVPixelBufferWidthKey:@640,
            (__bridge NSString *)kCVPixelBufferHeightKey:@360,
            (__bridge NSString *)kCVPixelBufferIOSurfacePropertiesKey:@{}
        };
        VTCompressionSessionRef session = NULL;
        printf("START mode=%s size=640x360 frames=60 fps=30\n", argv[1]);
        OSStatus status = VTCompressionSessionCreate(kCFAllocatorDefault,640,360,codec,
            (__bridge CFDictionaryRef)spec,(__bridge CFDictionaryRef)attrs,NULL,output,NULL,&session);
        printf("CREATE status=%d\n", (int)status);
        if (status) return 3;
        status = VTSessionSetProperty(session,kVTCompressionPropertyKey_RealTime,kCFBooleanTrue);
        if (!status) status = VTSessionSetProperty(session,kVTCompressionPropertyKey_AllowFrameReordering,kCFBooleanFalse);
        if (!status) status = VTCompressionSessionPrepareToEncodeFrames(session);
        printf("PREPARE status=%d\n", (int)status);
        CFTypeRef actual = NULL;
        OSStatus property = VTSessionCopyProperty(session,kVTCompressionPropertyKey_UsingHardwareAcceleratedVideoEncoder,NULL,&actual);
        bool usingHardware = actual && CFGetTypeID(actual)==CFBooleanGetTypeID() && CFBooleanGetValue(actual);
        printf("HARDWARE property_status=%d actual=%d expected=%d\n", (int)property,usingHardware,hardware);
        if (actual) CFRelease(actual);
        // Some software encoders do not expose this optional property.
        // Selection is already enforced by the encoder specification above.
        if (!status && !property && usingHardware != hardware) status = -1;
        for (int i=0; !status && i<60; ++i) {
            CVPixelBufferRef pixel = NULL;
            status = CVPixelBufferCreate(kCFAllocatorDefault,640,360,kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange,
                                        (__bridge CFDictionaryRef)attrs,&pixel);
            if (status) break;
            status = CVPixelBufferLockBaseAddress(pixel,0);
            if (!status) {
                for (size_t p=0;p<CVPixelBufferGetPlaneCount(pixel);++p)
                    memset(CVPixelBufferGetBaseAddressOfPlane(pixel,p), p ? 128 : 16+i,
                           CVPixelBufferGetBytesPerRowOfPlane(pixel,p)*CVPixelBufferGetHeightOfPlane(pixel,p));
                CVPixelBufferUnlockBaseAddress(pixel,0);
                status = VTCompressionSessionEncodeFrame(session,pixel,CMTimeMake(i,30),CMTimeMake(1,30),NULL,NULL,NULL);
            }
            CVPixelBufferRelease(pixel);
        }
        printf("SUBMIT status=%d\n",(int)status);
        OSStatus drain = VTCompressionSessionCompleteFrames(session,kCMTimeInvalid);
        VTCompressionSessionInvalidate(session); CFRelease(session); alarm(0);
        printf("RESULT submit=%d drain=%d frames=%u failed=%u\n",(int)status,(int)drain,atomic_load(&completed),atomic_load(&failures));
        return status || drain || atomic_load(&failures) || atomic_load(&completed)!=60 ? 4 : 0;
    }
}
