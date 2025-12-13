#!/usr/bin/env python3
"""
Create a test HTML page that plays audio and tests VAD
"""

html_content = '''
<!DOCTYPE html>
<html>
<head>
    <title>VAD Test</title>
</head>
<body>
    <h1>Testing Voice Activity Detection</h1>
    <button id="testBtn">Test VAD with Audio File</button>
    <div id="status"></div>
    <script>
        document.getElementById('testBtn').addEventListener('click', async () => {
            const status = document.getElementById('status');
            status.innerHTML = 'Starting test...';
            
            // Create audio context
            const audioContext = new AudioContext();
            await audioContext.resume();
            
            // Load test audio (use a sine wave for testing)
            const oscillator = audioContext.createOscillator();
            oscillator.frequency.value = 440; // A4 note
            
            // Create gain to control volume
            const gainNode = audioContext.createGain();
            gainNode.gain.value = 0.5;
            
            // Create media stream destination (this becomes a microphone input)
            const dest = audioContext.createMediaStreamDestination();
            
            oscillator.connect(gainNode);
            gainNode.connect(dest);
            
            // Create analyser to monitor
            const analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;
            gainNode.connect(analyser);
            
            // Create script processor
            const processor = audioContext.createScriptProcessor(4096, 1, 1);
            let volumes = [];
            
            processor.onaudioprocess = (e) => {
                const input = e.inputBuffer.getChannelData(0);
                let sum = 0;
                for (let i = 0; i < input.length; i++) {
                    sum += input[i] * input[i];
                }
                const volume = Math.sqrt(sum / input.length) * 100;
                volumes.push(volume);
                if (volumes.length % 10 === 0) {
                    status.innerHTML += `<br>Volume: ${volume.toFixed(2)}`;
                }
            };
            
            gainNode.connect(processor);
            processor.connect(audioContext.destination);
            
            // Start oscillator
            oscillator.start();
            status.innerHTML += '<br>Playing tone for 2 seconds...';
            
            setTimeout(() => {
                oscillator.stop();
                const avgVolume = volumes.reduce((a,b) => a+b, 0) / volumes.length;
                status.innerHTML += `<br><br>Average volume: ${avgVolume.toFixed(2)}`;
                status.innerHTML += `<br>Max volume: ${Math.max(...volumes).toFixed(2)}`;
                status.innerHTML += `<br><br>Stream tracks: ${dest.stream.getTracks().length}`;
                status.innerHTML += `<br>Audio track: ${dest.stream.getAudioTracks()[0].enabled}`;
            }, 2000);
        });
    </script>
</body>
</html>
'''

with open('/tmp/vad_test.html', 'w') as f:
    f.write(html_content)

print("Created test page: /tmp/vad_test.html")
print("This tests if ScriptProcessor can detect audio")

