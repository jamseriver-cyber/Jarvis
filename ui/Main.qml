import QtQuick
import QtQuick.Window
import QtMultimedia

Window {
    id: root

    property color cyan: "#38E8FF"
    property color cyanSoft: "#7FEFFF"
    property color green: "#6CFFCB"
    property color amber: "#FFC857"
    property color danger: "#FF6174"
    property color panelFill: "#C90A1722"
    property color panelEdge: "#7043DFF5"

    property string userText: "等待语音输入…"
    property string jarvisText: "系统在线。说“贾维斯”即可开始对话。"
    property string jarvisState: "READY"
    property string clockText: "00:00:00"
    property string dateText: ""
    property string networkText: "0 B/s"
    property string uptimeText: "0D 00H 00M"
    property string modelName: "qwen3.5:0.8b"
    property string currentActivityApp: "LOCAL MEMORY"
    property string currentActivityTitle: "等待记录前台活动…"
    property string nextReminderTime: "--:--"
    property string nextReminderText: "暂无待处理提醒"
    property string reminderAlertTime: "--:--"
    property string reminderAlertText: ""
    property string lastToolText: "工具系统待命"
    property bool lastToolSuccess: true
    property real cpuValue: 0
    property real memoryValue: 0
    property real diskValue: 0
    property real audioLevel: 0
    property real wavePhase: 0
    property bool llmOnline: false
    property bool waitingForAck: false

    readonly property color stateColor: {
        if (jarvisState === "ERROR") return danger
        if (jarvisState === "THINKING" || jarvisState === "TRANSCRIBING" || jarvisState === "REMINDER") return amber
        if (jarvisState === "EXECUTING") return green
        if (jarvisState === "SPEAKING" || jarvisState === "RESPONDING") return green
        return cyan
    }

    readonly property string stateCaption: {
        if (jarvisState === "ACTIVATING") return "正在建立语音通道"
        if (jarvisState === "LISTENING") return "正在聆听，请说出指令"
        if (jarvisState === "TRANSCRIBING") return "正在解析语音信号"
        if (jarvisState === "THINKING") return "本地 AI 核心正在推理"
        if (jarvisState === "EXECUTING") return "正在执行真实世界任务"
        if (jarvisState === "REMINDER") return "个人提醒已到时间"
        if (jarvisState === "RESPONDING") return "正在生成回复"
        if (jarvisState === "SYNTHESIZING") return "正在准备本地语音"
        if (jarvisState === "SPEAKING") return "Jarvis 正在回应"
        if (jarvisState === "ERROR") return "链路异常，请查看对话面板"
        return "待命中 · 唤醒词：贾维斯"
    }

    width: jarvisPreview ? 1600 : Screen.width
    height: jarvisPreview ? 900 : Screen.height
    minimumWidth: 1180
    minimumHeight: 700
    visible: jarvisPreview
    visibility: jarvisPreview ? Window.Windowed : Window.Hidden
    color: "transparent"
    flags: jarvisPreview
           ? Qt.FramelessWindowHint
           : Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus
    title: "Personal Jarvis // Neural Interface"

    component HudPanel: Rectangle {
        property string panelTitle: "PANEL"
        property string panelCode: "SYS-00"

        radius: 12
        color: root.panelFill
        border.color: root.panelEdge
        border.width: 1

        Rectangle {
            width: 46
            height: 2
            color: root.cyan
            anchors.left: parent.left
            anchors.top: parent.top
        }
        Rectangle {
            width: 2
            height: 24
            color: root.cyan
            anchors.left: parent.left
            anchors.top: parent.top
        }
        Rectangle {
            width: 30
            height: 2
            color: root.cyan
            anchors.right: parent.right
            anchors.bottom: parent.bottom
        }
        Rectangle {
            width: 2
            height: 18
            color: root.cyan
            anchors.right: parent.right
            anchors.bottom: parent.bottom
        }

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 20
            anchors.top: parent.top
            anchors.topMargin: 16
            text: parent.panelTitle
            color: root.cyan
            font.family: "Bahnschrift"
            font.pixelSize: 13
            font.bold: true
            font.letterSpacing: 2.4
        }
        Text {
            anchors.right: parent.right
            anchors.rightMargin: 18
            anchors.top: parent.top
            anchors.topMargin: 17
            text: parent.panelCode
            color: "#688FA0AA"
            font.family: "Consolas"
            font.pixelSize: 10
            font.letterSpacing: 1
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            anchors.top: parent.top
            anchors.topMargin: 45
            height: 1
            color: "#3049DDF2"
        }
    }

    component MetricRow: Item {
        property string metricName: "CPU LOAD"
        property real metricValue: 0
        property string metricSuffix: Math.round(metricValue) + "%"

        height: 58
        Text {
            anchors.left: parent.left
            anchors.top: parent.top
            text: parent.metricName
            color: "#88A9BCC7"
            font.family: "Bahnschrift"
            font.pixelSize: 11
            font.letterSpacing: 1.2
        }
        Text {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: -4
            text: parent.metricSuffix
            color: root.cyanSoft
            font.family: "Consolas"
            font.pixelSize: 18
            font.bold: true
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: 27
            height: 5
            radius: 2
            color: "#2038BFD5"
            Rectangle {
                width: Math.max(4, parent.width * Math.min(100, Math.max(0, metricValue)) / 100)
                height: parent.height
                radius: parent.radius
                color: metricValue > 85 ? root.danger : root.cyan
                Behavior on width { NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }
            }
        }
        Row {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.topMargin: 39
            spacing: 3
            Repeater {
                model: 12
                Rectangle {
                    width: 9
                    height: 2
                    color: index / 12 < metricValue / 100 ? "#7557E9FA" : "#152C7180"
                }
            }
        }
    }

    component ModuleRow: Item {
        property string moduleName: "MODULE"
        property string moduleState: "ONLINE"
        property bool online: true

        height: 31
        Rectangle {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: 5
            height: 5
            radius: 3
            color: parent.online ? root.green : root.danger
        }
        Text {
            anchors.left: parent.left
            anchors.leftMargin: 15
            anchors.verticalCenter: parent.verticalCenter
            text: parent.moduleName
            color: "#A7BED0DC"
            font.family: "Bahnschrift"
            font.pixelSize: 11
            font.letterSpacing: 0.8
        }
        Text {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: parent.moduleState
            color: parent.online ? root.green : root.danger
            font.family: "Consolas"
            font.pixelSize: 11
            font.bold: true
        }
    }

    MediaPlayer {
        id: wakeAck
        source: Qt.resolvedUrl("../assets/sounds/wake_ack.wav")
        audioOutput: AudioOutput { volume: 0.9 }

        onPlaybackStateChanged: {
            if (playbackState === MediaPlayer.StoppedState && root.waitingForAck) {
                root.waitingForAck = false
                ackFallback.stop()
                jarvisBridge.ackFinished()
            }
        }
        onErrorOccurred: function(error, errorString) {
            console.log("Wake audio error:", errorString)
            if (root.waitingForAck) ackFallback.restart()
        }
    }

    Timer {
        id: ackFallback
        interval: 1800
        repeat: false
        onTriggered: {
            if (root.waitingForAck) {
                root.waitingForAck = false
                jarvisBridge.ackFinished()
            }
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            var now = new Date()
            root.clockText = Qt.formatDateTime(now, "hh:mm:ss")
            root.dateText = Qt.formatDateTime(now, "yyyy.MM.dd  dddd").toUpperCase()
        }
    }

    Timer {
        interval: 70
        running: hud.visible
        repeat: true
        onTriggered: root.wavePhase += 0.22
    }

    Timer {
        id: idleHide
        repeat: false
        onTriggered: root.hideHud()
    }

    function scheduleHide(delayMs) {
        if (!jarvisPreview && root.visible) {
            idleHide.interval = delayMs
            idleHide.restart()
        }
    }

    function showHud() {
        idleHide.stop()
        fadeOut.stop()
        if (!jarvisPreview && !root.visible) root.showFullScreen()
        hud.visible = true
        fadeIn.restart()
    }

    function hideHud() {
        if (jarvisPreview) return
        idleHide.stop()
        fadeIn.stop()
        if (root.visible && hud.visible) fadeOut.restart()
        else {
            hud.visible = false
            hud.opacity = 0
            root.hide()
        }
    }

    function toggleHud() {
        if (root.visible && hud.visible) hideHud()
        else showHud()
    }

    Item {
        id: hud
        anchors.fill: parent
        visible: jarvisPreview
        opacity: jarvisPreview ? 1 : 0

        Rectangle {
            anchors.fill: parent
            color: "#F2070E15"
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#F0061019" }
                GradientStop { position: 0.52; color: "#F40A1821" }
                GradientStop { position: 1.0; color: "#F2040B12" }
            }
        }

        Canvas {
            id: gridCanvas
            anchors.fill: parent
            opacity: 0.23
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.strokeStyle = "#2E38BFD5"
                ctx.lineWidth = 1
                var gap = 54
                for (var x = 0; x < width; x += gap) {
                    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke()
                }
                for (var y = 0; y < height; y += gap) {
                    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
                }
                ctx.strokeStyle = "#4A38E8FF"
                ctx.beginPath(); ctx.moveTo(width / 2, 0); ctx.lineTo(width / 2, height); ctx.stroke()
                ctx.beginPath(); ctx.moveTo(0, height / 2); ctx.lineTo(width, height / 2); ctx.stroke()
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 3
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "transparent" }
                GradientStop { position: 0.5; color: root.cyan }
                GradientStop { position: 1; color: "transparent" }
            }
        }

        Item {
            id: topBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 42
            anchors.rightMargin: 42
            anchors.topMargin: 25
            height: 62

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 15
                Rectangle {
                    width: 38
                    height: 38
                    radius: 19
                    color: "#1538E8FF"
                    border.color: root.cyan
                    border.width: 1
                    Rectangle {
                        anchors.centerIn: parent
                        width: 12
                        height: 12
                        radius: 6
                        color: root.cyan
                    }
                }
                Column {
                    spacing: 1
                    Text {
                        text: "J.A.R.V.I.S"
                        color: "white"
                        font.family: "Bahnschrift"
                        font.pixelSize: 22
                        font.bold: true
                        font.letterSpacing: 4
                    }
                    Text {
                        text: "PERSONAL NEURAL INTERFACE  /  V0.2.0"
                        color: "#758FAAB7"
                        font.family: "Consolas"
                        font.pixelSize: 9
                        font.letterSpacing: 1.4
                    }
                }
            }

            Column {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                spacing: -2
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.clockText
                    color: "white"
                    font.family: "Consolas"
                    font.pixelSize: 25
                    font.bold: true
                    font.letterSpacing: 4
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.dateText
                    color: "#6F98ACB8"
                    font.family: "Consolas"
                    font.pixelSize: 9
                    font.letterSpacing: 1.2
                }
            }

            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 14
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    Text {
                        anchors.right: parent.right
                        text: "LOCAL SECURE LINK"
                        color: root.green
                        font.family: "Bahnschrift"
                        font.pixelSize: 11
                        font.bold: true
                        font.letterSpacing: 1.4
                    }
                    Text {
                        anchors.right: parent.right
                        text: "VOICE DATA STAYS ON DEVICE"
                        color: "#658FA7B4"
                        font.family: "Consolas"
                        font.pixelSize: 9
                    }
                }
                Rectangle {
                    width: 9
                    height: 9
                    radius: 5
                    color: root.green
                    SequentialAnimation on opacity {
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.25; duration: 700 }
                        NumberAnimation { to: 1; duration: 700 }
                    }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: "#3438DFF5"
            }
        }

        Rectangle {
            id: reminderAlert
            z: 50
            width: Math.min(560, root.width * 0.42)
            height: 86
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: topBar.bottom
            anchors.topMargin: 10
            radius: 10
            color: "#ED241A0A"
            border.color: root.amber
            border.width: 1
            visible: opacity > 0
            opacity: 0

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 4
                color: root.amber
            }
            Column {
                anchors.left: parent.left
                anchors.leftMargin: 22
                anchors.right: parent.right
                anchors.rightMargin: 18
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6
                Text {
                    text: "◈  PERSONAL REMINDER  //  " + root.reminderAlertTime
                    color: root.amber
                    font.family: "Bahnschrift"
                    font.pixelSize: 11
                    font.bold: true
                    font.letterSpacing: 1.5
                }
                Text {
                    width: parent.width
                    text: root.reminderAlertText
                    color: "white"
                    font.family: "Microsoft YaHei UI"
                    font.pixelSize: 17
                    font.bold: true
                    elide: Text.ElideRight
                }
            }
            Behavior on opacity { NumberAnimation { duration: 220 } }
        }

        Timer {
            id: reminderHideTimer
            interval: 12000
            repeat: false
            onTriggered: {
                reminderAlert.opacity = 0
                if (root.jarvisState === "REMINDER") root.jarvisState = "READY"
                root.scheduleHide(3000)
            }
        }

        HudPanel {
            id: systemPanel
            panelTitle: "SYSTEM TELEMETRY"
            panelCode: "SYS-01"
            width: Math.max(270, Math.min(310, root.width * 0.195))
            anchors.left: parent.left
            anchors.leftMargin: 42
            anchors.top: topBar.bottom
            anchors.topMargin: 18
            anchors.bottom: footer.top
            anchors.bottomMargin: 16

            Column {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                anchors.top: parent.top
                anchors.topMargin: 63
                spacing: 0

                MetricRow {
                    width: parent.width
                    metricName: "PROCESSOR LOAD"
                    metricValue: root.cpuValue
                }
                MetricRow {
                    width: parent.width
                    metricName: "MEMORY MATRIX"
                    metricValue: root.memoryValue
                }
                MetricRow {
                    width: parent.width
                    metricName: "SYSTEM STORAGE"
                    metricValue: root.diskValue
                }

                Rectangle { width: parent.width; height: 1; color: "#3049DDF2" }

                Item {
                    width: parent.width
                    height: 66
                    Text {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.topMargin: 13
                        text: "NETWORK RECEIVE"
                        color: "#88A9BCC7"
                        font.family: "Bahnschrift"
                        font.pixelSize: 11
                        font.letterSpacing: 1.1
                    }
                    Text {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.topMargin: 10
                        text: "↓ " + root.networkText
                        color: root.cyanSoft
                        font.family: "Consolas"
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Text {
                        anchors.left: parent.left
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 9
                        text: "UPTIME"
                        color: "#668DA5B2"
                        font.family: "Bahnschrift"
                        font.pixelSize: 10
                    }
                    Text {
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 7
                        text: root.uptimeText
                        color: "#B8D3E0E7"
                        font.family: "Consolas"
                        font.pixelSize: 11
                    }
                }

                Rectangle { width: parent.width; height: 1; color: "#3049DDF2" }
                Item { width: 1; height: 12 }
                ModuleRow {
                    width: parent.width
                    moduleName: "AI CORE"
                    moduleState: root.llmOnline ? "ONLINE" : "STANDBY"
                    online: root.llmOnline
                }
                ModuleRow {
                    width: parent.width
                    moduleName: "WHISPER STT"
                    moduleState: "READY"
                    online: true
                }
                ModuleRow {
                    width: parent.width
                    moduleName: "LOCAL VOICE"
                    moduleState: "SAPI"
                    online: true
                }
                ModuleRow {
                    width: parent.width
                    moduleName: "WAKE SENSOR"
                    moduleState: "ARMED"
                    online: true
                }
                ModuleRow {
                    width: parent.width
                    moduleName: "MEMORY + TOOLS"
                    moduleState: "ACTIVE"
                    online: true
                }

                Item { width: 1; height: 9 }
                Rectangle { width: parent.width; height: 1; color: "#3049DDF2" }
                Item { width: 1; height: 12 }

                Text {
                    text: "PERSONAL CONTEXT"
                    color: root.cyan
                    font.family: "Bahnschrift"
                    font.pixelSize: 10
                    font.bold: true
                    font.letterSpacing: 1.5
                }
                Item { width: 1; height: 9 }
                Text {
                    width: parent.width
                    text: root.currentActivityApp.toUpperCase() + "  //  NOW"
                    color: "#728FA7B4"
                    font.family: "Consolas"
                    font.pixelSize: 9
                    elide: Text.ElideRight
                }
                Text {
                    width: parent.width
                    text: root.currentActivityTitle
                    color: "#D1E8F1F6"
                    font.family: "Microsoft YaHei UI"
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                    lineHeight: 1.25
                }
                Item { width: 1; height: 12 }
                Row {
                    width: parent.width
                    spacing: 9
                    Rectangle {
                        width: 5
                        height: 5
                        radius: 3
                        color: root.nextReminderTime === "--:--" ? "#536F8290" : root.amber
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: "NEXT  " + root.nextReminderTime
                        color: root.nextReminderTime === "--:--" ? "#668DA5B2" : root.amber
                        font.family: "Consolas"
                        font.pixelSize: 10
                        font.bold: true
                    }
                }
                Text {
                    width: parent.width
                    text: root.nextReminderText
                    color: "#A8C0CDD5"
                    font.family: "Microsoft YaHei UI"
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }
            }
        }

        Item {
            id: centerStage
            anchors.left: systemPanel.right
            anchors.right: conversationPanel.left
            anchors.leftMargin: 22
            anchors.rightMargin: 22
            anchors.top: topBar.bottom
            anchors.topMargin: 18
            anchors.bottom: footer.top
            anchors.bottomMargin: 16

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                text: "NEURAL VOICE CORE"
                color: "#688FA8B5"
                font.family: "Bahnschrift"
                font.pixelSize: 10
                font.letterSpacing: 3.2
            }

            Item {
                id: core
                width: Math.min(parent.width * 0.74, parent.height * 0.63)
                height: width
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: -26

                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 0.92
                    height: width
                    radius: width / 2
                    color: "#0438E8FF"
                    border.color: "#1538E8FF"
                }
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 0.73
                    height: width
                    radius: width / 2
                    color: "transparent"
                    border.color: "#2448DDF2"
                    border.width: 1
                }

                Canvas {
                    id: segmentedRing
                    anchors.fill: parent
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.reset()
                        ctx.lineWidth = Math.max(2, width * 0.009)
                        ctx.strokeStyle = root.stateColor
                        var radius = width * 0.43
                        for (var i = 0; i < 18; i++) {
                            var start = (i * 20 + 2) * Math.PI / 180
                            var end = (i * 20 + 13) * Math.PI / 180
                            ctx.beginPath()
                            ctx.arc(width / 2, height / 2, radius, start, end)
                            ctx.stroke()
                        }
                    }
                    RotationAnimation on rotation {
                        from: 0
                        to: 360
                        duration: root.jarvisState === "THINKING" ? 4200 : 12000
                        loops: Animation.Infinite
                    }
                }

                Canvas {
                    anchors.centerIn: parent
                    width: parent.width * 0.67
                    height: width
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.reset()
                        ctx.lineWidth = 2
                        ctx.strokeStyle = "#A138E8FF"
                        var radius = width * 0.46
                        for (var i = 0; i < 8; i++) {
                            var start = (i * 45 + 8) * Math.PI / 180
                            var end = (i * 45 + 34) * Math.PI / 180
                            ctx.beginPath(); ctx.arc(width / 2, height / 2, radius, start, end); ctx.stroke()
                        }
                    }
                    RotationAnimation on rotation {
                        from: 360
                        to: 0
                        duration: 8000
                        loops: Animation.Infinite
                    }
                }

                Repeater {
                    model: 24
                    Rectangle {
                        required property int index
                        width: index % 3 === 0 ? 18 : 8
                        height: 2
                        radius: 1
                        color: index % 3 === 0 ? root.stateColor : "#7448DFF2"
                        x: core.width / 2 - width / 2
                        y: core.height * 0.075
                        transformOrigin: Item.Center
                        rotation: index * 15
                        transform: Translate { y: core.height / 2 - core.height * 0.075 }
                    }
                }

                Rectangle {
                    id: reactorHalo
                    anchors.centerIn: parent
                    width: parent.width * 0.45
                    height: width
                    radius: width / 2
                    color: root.jarvisState === "SPEAKING" ? "#126CFFCB" : "#1238E8FF"
                    border.color: "#5938E8FF"
                    border.width: 1
                    SequentialAnimation on scale {
                        running: hud.visible
                        loops: Animation.Infinite
                        NumberAnimation {
                            to: root.jarvisState === "LISTENING" ? 1.07 : 1.035
                            duration: 620
                            easing.type: Easing.InOutSine
                        }
                        NumberAnimation { to: 1.0; duration: 620; easing.type: Easing.InOutSine }
                    }
                }
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 0.31
                    height: width
                    radius: width / 2
                    color: "#1A38E8FF"
                    border.color: root.stateColor
                    border.width: 2
                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width * 0.72
                        height: width
                        radius: width / 2
                        color: "#2538E8FF"
                        border.color: "#B838E8FF"
                        border.width: 1
                    }
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 4
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "JARVIS"
                        color: "white"
                        font.family: "Bahnschrift"
                        font.pixelSize: Math.max(18, core.width * 0.06)
                        font.bold: true
                        font.letterSpacing: 3.5
                    }
                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 54
                        height: 1
                        color: root.stateColor
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.jarvisState
                        color: root.stateColor
                        font.family: "Consolas"
                        font.pixelSize: Math.max(10, core.width * 0.026)
                        font.bold: true
                        font.letterSpacing: 2.2
                    }
                }
            }

            Column {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                spacing: 10
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.stateCaption
                    color: root.stateColor
                    font.family: "Microsoft YaHei UI"
                    font.pixelSize: 13
                    font.bold: true
                    font.letterSpacing: 1.2
                }
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    height: 58
                    spacing: 5
                    Repeater {
                        model: 35
                        Rectangle {
                            required property int index
                            anchors.verticalCenter: parent.verticalCenter
                            width: 4
                            radius: 2
                            height: {
                                var active = root.jarvisState === "LISTENING" ? root.audioLevel :
                                             (root.jarvisState === "SPEAKING" || root.jarvisState === "RESPONDING" ? 0.72 : 0.18)
                                var shape = Math.abs(Math.sin(root.wavePhase + index * 0.48))
                                var envelope = 0.35 + 0.65 * Math.sin((index + 1) / 36 * Math.PI)
                                return 4 + shape * envelope * (10 + active * 42)
                            }
                            color: root.stateColor
                            opacity: 0.35 + 0.65 * Math.sin((index + 1) / 36 * Math.PI)
                            Behavior on height { NumberAnimation { duration: 65 } }
                        }
                    }
                }
            }
        }

        HudPanel {
            id: conversationPanel
            panelTitle: "LIVE DIALOGUE"
            panelCode: "COM-02"
            width: Math.max(340, Math.min(410, root.width * 0.255))
            anchors.right: parent.right
            anchors.rightMargin: 42
            anchors.top: topBar.bottom
            anchors.topMargin: 18
            anchors.bottom: footer.top
            anchors.bottomMargin: 16

            Rectangle {
                id: userCard
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                anchors.top: parent.top
                anchors.topMargin: 64
                height: 126
                radius: 8
                color: "#560C2531"
                border.color: "#3443DFF5"
                border.width: 1

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    anchors.top: parent.top
                    anchors.topMargin: 12
                    text: "YOU  //  INPUT STREAM"
                    color: root.cyan
                    font.family: "Bahnschrift"
                    font.pixelSize: 10
                    font.bold: true
                    font.letterSpacing: 1.3
                }
                Text {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.margins: 14
                    anchors.topMargin: 38
                    text: root.userText
                    color: "#EBF8FCFF"
                    font.family: "Microsoft YaHei UI"
                    font.pixelSize: 16
                    lineHeight: 1.35
                    wrapMode: Text.WordWrap
                    elide: Text.ElideRight
                    maximumLineCount: 3
                }
            }

            Rectangle {
                id: jarvisCard
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                anchors.top: userCard.bottom
                anchors.topMargin: 14
                anchors.bottom: modelCard.top
                anchors.bottomMargin: 14
                radius: 8
                color: "#73101F28"
                border.color: root.jarvisState === "ERROR" ? "#70FF6174" : "#4056F2C4"
                border.width: 1

                Row {
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    anchors.top: parent.top
                    anchors.topMargin: 12
                    spacing: 8
                    Rectangle {
                        width: 6
                        height: 6
                        radius: 3
                        color: root.stateColor
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: "JARVIS  //  RESPONSE"
                        color: root.green
                        font.family: "Bahnschrift"
                        font.pixelSize: 10
                        font.bold: true
                        font.letterSpacing: 1.3
                    }
                }

                Flickable {
                    id: responseFlick
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    anchors.topMargin: 40
                    anchors.bottomMargin: 13
                    contentWidth: width
                    contentHeight: responseText.height
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    Text {
                        id: responseText
                        width: responseFlick.width
                        text: root.jarvisText
                        color: "#F1F9FCFF"
                        font.family: "Microsoft YaHei UI"
                        font.pixelSize: 16
                        lineHeight: 1.4
                        wrapMode: Text.WordWrap
                    }
                }
            }

            Rectangle {
                id: modelCard
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 19
                height: 76
                radius: 8
                color: "#480B1A24"
                border.color: "#3043DFF5"

                Column {
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4
                    Text {
                        text: "LOCAL INFERENCE MODEL"
                        color: "#668DA5B2"
                        font.family: "Bahnschrift"
                        font.pixelSize: 9
                        font.letterSpacing: 1.2
                    }
                    Text {
                        text: root.modelName
                        color: "#D9F2FAFF"
                        font.family: "Consolas"
                        font.pixelSize: 15
                        font.bold: true
                    }
                }
                Column {
                    anchors.right: parent.right
                    anchors.rightMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4
                    Text {
                        anchors.right: parent.right
                        text: "CONNECTION"
                        color: "#668DA5B2"
                        font.family: "Bahnschrift"
                        font.pixelSize: 9
                    }
                    Text {
                        anchors.right: parent.right
                        text: root.llmOnline ? "ONLINE" : "STANDBY"
                        color: root.llmOnline ? root.green : root.amber
                        font.family: "Consolas"
                        font.pixelSize: 12
                        font.bold: true
                    }
                }
            }
        }

        Item {
            id: footer
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 42
            anchors.rightMargin: 42
            anchors.bottomMargin: 17
            height: 36

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 1
                color: "#3438DFF5"
            }
            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: 4
                spacing: 18
                Text {
                    text: "●  SYSTEM ONLINE"
                    color: root.green
                    font.family: "Consolas"
                    font.pixelSize: 10
                    font.bold: true
                    font.letterSpacing: 1.2
                }
                Text {
                    text: "STT  LOCAL"
                    color: "#6F98ACB8"
                    font.family: "Consolas"
                    font.pixelSize: 10
                }
                Text {
                    text: "LLM  LOCAL"
                    color: "#6F98ACB8"
                    font.family: "Consolas"
                    font.pixelSize: 10
                }
                Text {
                    text: "TTS  LOCAL"
                    color: "#6F98ACB8"
                    font.family: "Consolas"
                    font.pixelSize: 10
                }
            }
            Text {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: 4
                text: "MOUSE  PASSTHROUGH  ●     F8  HUD     F9  PUSH TO TALK"
                color: "#7698AFBB"
                font.family: "Consolas"
                font.pixelSize: 10
                font.letterSpacing: 1.1
            }
        }
    }

    NumberAnimation {
        id: fadeIn
        target: hud
        property: "opacity"
        from: 0
        to: 1
        duration: 320
        easing.type: Easing.OutCubic
    }
    NumberAnimation {
        id: fadeOut
        target: hud
        property: "opacity"
        from: 1
        to: 0
        duration: 300
        onFinished: {
            hud.visible = false
            hud.opacity = 0
            if (!jarvisPreview) root.hide()
        }
    }

    Connections {
        target: jarvisBridge

        function onToggleHud() { root.toggleHud() }
        function onShowHudRequested() { root.showHud() }
        function onHideHudRequested() { root.hideHud() }

        function onWakeDetected(keyword) {
            root.showHud()
            root.jarvisState = "ACTIVATING"
            root.userText = "语音通道已激活，等待指令…"
            root.jarvisText = "我在。"
            wakeAck.stop()
            root.waitingForAck = true
            ackFallback.restart()
            wakeAck.play()
        }

        function onListeningStarted() {
            root.jarvisState = "LISTENING"
            root.userText = "正在聆听…"
        }

        function onTranscribingStarted() {
            root.jarvisState = "TRANSCRIBING"
            root.userText = "正在识别语音…"
        }

        function onTranscriptReady(text) {
            root.userText = text.length > 0 ? text : "未识别到有效内容"
        }

        function onNoSpeech() {
            root.jarvisState = "READY"
            root.userText = "未检测到有效语音，请重新唤醒。"
            root.jarvisText = "没有听清，请再说一次。"
            root.scheduleHide(3000)
        }

        function onLlmStarted() {
            root.jarvisState = "THINKING"
            root.jarvisText = "正在连接本地 AI 核心…"
        }

        function onLlmChunk(chunk) {
            if (root.jarvisState === "THINKING" || root.jarvisState === "EXECUTING" || root.jarvisState === "REMINDER") {
                root.jarvisText = ""
                root.jarvisState = "RESPONDING"
            }
            root.jarvisText += chunk
            responseFlick.contentY = Math.max(0, responseFlick.contentHeight - responseFlick.height)
        }

        function onLlmFinished(text) {
            root.jarvisText = text
            root.jarvisState = "SYNTHESIZING"
        }

        function onLlmError(message) {
            root.jarvisText = "AI 核心连接失败。\n" + message
            root.jarvisState = "ERROR"
            root.scheduleHide(12000)
        }

        function onTtsStarted() { root.jarvisState = "SPEAKING" }
        function onTtsFinished() {
            root.jarvisState = "READY"
            root.scheduleHide(4500)
        }
        function onTtsError(message) {
            root.jarvisState = "READY"
            console.log("TTS error:", message)
            root.scheduleHide(4500)
        }

        function onAudioLevelChanged(level) { root.audioLevel = level }
        function onSystemMetrics(cpu, memory, disk, network, uptime) {
            root.cpuValue = cpu
            root.memoryValue = memory
            root.diskValue = disk
            root.networkText = network
            root.uptimeText = uptime
        }
        function onLlmStatusChanged(online, model) {
            root.llmOnline = online
            root.modelName = model
        }
        function onToolStarted(tool, detail) {
            root.jarvisState = "EXECUTING"
            root.jarvisText = "正在执行：" + tool + "…"
            root.lastToolText = tool + "  RUNNING"
            root.lastToolSuccess = true
            if (tool === "open_application" || tool === "open_calendar"
                    || tool === "search_web" || tool === "open_browser") {
                root.hideHud()
            }
        }
        function onToolFinished(tool, success, message) {
            root.lastToolText = tool + "  " + (success ? "DONE" : "FAILED")
            root.lastToolSuccess = success
            if (success && (tool === "hide_hud" || tool === "open_application"
                            || tool === "open_calendar" || tool === "search_web"
                            || tool === "open_browser")) {
                root.hideHud()
            } else if (!success && (tool === "open_application" || tool === "open_calendar"
                                    || tool === "search_web" || tool === "open_browser")) {
                root.showHud()
            }
        }
        function onActivityChanged(app, title) {
            root.currentActivityApp = app
            root.currentActivityTitle = title
        }
        function onNextReminderChanged(time, message) {
            root.nextReminderTime = time
            root.nextReminderText = message
        }
        function onReminderTriggered(time, message) {
            root.showHud()
            root.reminderAlertTime = time
            root.reminderAlertText = message
            root.jarvisState = "REMINDER"
            root.jarvisText = "提醒你：" + message
            reminderAlert.opacity = 1
            reminderHideTimer.restart()
        }
    }

    Component.onCompleted: {
        if (jarvisPreview) {
            root.cpuValue = 28
            root.memoryValue = 46
            root.diskValue = 39
            root.networkText = "1.8 MB/s"
            root.uptimeText = "2D 14H 37M"
            root.llmOnline = true
            root.userText = "贾维斯，简单介绍一下当前系统状态。"
            root.jarvisText = "所有核心模块运行正常。本地模型、语音识别与离线语音链路均已就绪。"
            root.currentActivityApp = "Visual Studio Code"
            root.currentActivityTitle = "PersonalJarvis · assistant_tools.py"
            root.nextReminderTime = "17:00"
            root.nextReminderText = "参加项目会议"
            root.lastToolText = "TOOLS  ACTIVE"
            root.jarvisState = "READY"
            root.showHud()
        }
    }
}
