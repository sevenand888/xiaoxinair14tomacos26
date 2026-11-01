// SPDX-License-Identifier: BSD-3-Clause
// IOAudioFamily layer adapted from LatSOFKernelAudio. See LICENSE.donor.
#pragma once
#include <IOKit/audio/IOAudioDevice.h>
#include <IOKit/audio/IOAudioEngine.h>
#include <IOKit/audio/IOAudioStream.h>
#include <IOKit/audio/IOAudioLevelControl.h>
#include <IOKit/audio/IOAudioToggleControl.h>
#include <IOKit/audio/IOAudioSelectorControl.h>
class Lenovo82FFSSTMicrophone;
class Lenovo82FFMicAudioEngine;
class Lenovo82FFMicAudioDevice:public IOAudioDevice {
    OSDeclareDefaultStructors(Lenovo82FFMicAudioDevice)
    Lenovo82FFSSTMicrophone *owner_=nullptr;
    Lenovo82FFMicAudioEngine *engine_=nullptr;
public:
    bool initWithOwner(Lenovo82FFSSTMicrophone *);
    bool initHardware(IOService *) override;
    void stop(IOService *) override;
    IOWorkLoop *getWorkLoop() const override;
    Lenovo82FFMicAudioEngine *engine(){return engine_;}
    void clearEngine(){engine_=nullptr;}
};
class Lenovo82FFMicAudioEngine:public IOAudioEngine {
    OSDeclareDefaultStructors(Lenovo82FFMicAudioEngine)
    Lenovo82FFSSTMicrophone *owner_=nullptr;
    IOTimerEventSource *timer_=nullptr;
    RazerPCM::Filter *filter_=nullptr;
    volatile SInt32 gainDB_=30,muted_=0;
    bool running_=false,resumeWanted_=false;
    UInt32 lastFrame_=0,clockMisses_=0;
    UInt64 lastTickNS_=0,lastProgressNS_=0;
    void stamp(bool,AbsoluteTime,UInt32);
    bool edgePosition(UInt32 &,AbsoluteTime &);
    static void tick(OSObject *,IOTimerEventSource *);
    static IOReturn gainChanged(OSObject *,IOAudioControl *,SInt32,SInt32);
    static IOReturn muteChanged(OSObject *,IOAudioControl *,SInt32,SInt32);
public:
    bool initWithOwner(Lenovo82FFSSTMicrophone *);
    bool initHardware(IOService *) override;
    void stop(IOService *) override;
    void free() override;
    IOReturn performAudioEngineStart() override;
    IOReturn performAudioEngineStop() override;
    UInt32 getCurrentSampleFrame() override;
    OSString *getGlobalUniqueID() override {return OSString::withCString("Lenovo82FFSSTMicrophone:8086-A0C8:17AA-381D:PDM0");}
    IOReturn performFormatChange(IOAudioStream *,const IOAudioStreamFormat *,const IOAudioSampleRate *) override;
    IOReturn convertInputSamples(const void *,void *,UInt32,UInt32,const IOAudioStreamFormat *,IOAudioStream *) override;
    void prepareForSleep();
    bool resumeIfNeeded();
};
