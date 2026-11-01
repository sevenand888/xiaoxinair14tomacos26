#import <Foundation/Foundation.h>
#import <CoreAudio/CoreAudio.h>

static NSString *StringProperty(AudioDeviceID device, AudioObjectPropertySelector selector) {
    AudioObjectPropertyAddress a={selector,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
    CFStringRef value=NULL; UInt32 size=sizeof(value);
    if(AudioObjectGetPropertyData(device,&a,0,NULL,&size,&value)||!value)return @"";
    return CFBridgingRelease(value);
}
int main(int argc, const char **argv) { @autoreleasepool {
    if(argc!=2){fprintf(stderr,"Usage: select-input-uid exact-input-uid\n");return 2;}
    AudioObjectPropertyAddress a={kAudioHardwarePropertyDevices,kAudioObjectPropertyScopeGlobal,kAudioObjectPropertyElementMain};
    UInt32 size=0;
    if(AudioObjectGetPropertyDataSize(kAudioObjectSystemObject,&a,0,NULL,&size))return 3;
    AudioDeviceID *ids=malloc(size); if(!ids)return 4;
    if(AudioObjectGetPropertyData(kAudioObjectSystemObject,&a,0,NULL,&size,ids)){free(ids);return 5;}
    AudioDeviceID found=0;
    for(UInt32 i=0;i<size/sizeof(*ids);i++){
        if(![StringProperty(ids[i],kAudioDevicePropertyDeviceUID) isEqualToString:@(argv[1])])continue;
        AudioObjectPropertyAddress c={kAudioDevicePropertyStreamConfiguration,kAudioDevicePropertyScopeInput,kAudioObjectPropertyElementMain};
        UInt32 n=0,channels=0;
        if(AudioObjectGetPropertyDataSize(ids[i],&c,0,NULL,&n)||!n)continue;
        AudioBufferList *list=malloc(n); if(!list)continue;
        if(!AudioObjectGetPropertyData(ids[i],&c,0,NULL,&n,list))
            for(UInt32 b=0;b<list->mNumberBuffers;b++)channels+=list->mBuffers[b].mNumberChannels;
        free(list); if(channels)found=ids[i];
    }
    free(ids);if(!found){fprintf(stderr,"Exact input UID absent\n");return 6;}
    a.mSelector=kAudioHardwarePropertyDefaultInputDevice;
    AudioDeviceID before=0;size=sizeof(before);
    OSStatus status=AudioObjectGetPropertyData(kAudioObjectSystemObject,&a,0,NULL,&size,&before);
    if(status)return 7;
    printf("before_uid=%s\n",StringProperty(before,kAudioDevicePropertyDeviceUID).UTF8String);
    status=AudioObjectSetPropertyData(kAudioObjectSystemObject,&a,0,NULL,sizeof(found),&found);
    if(status){fprintf(stderr,"Set default input error %d\n",(int)status);return 8;}
    AudioDeviceID actual=0;size=sizeof(actual);
    status=AudioObjectGetPropertyData(kAudioObjectSystemObject,&a,0,NULL,&size,&actual);
    if(status)return 9;
    NSString *uid=StringProperty(actual,kAudioDevicePropertyDeviceUID);
    printf("after_uid=%s\nname=%s\nvolume_and_mute_unchanged=true\n",uid.UTF8String,StringProperty(actual,kAudioObjectPropertyName).UTF8String);
    return actual==found && [uid isEqualToString:@(argv[1])]?0:10;
} }
