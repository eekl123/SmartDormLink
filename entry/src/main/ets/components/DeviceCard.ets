import { DeviceState, DEVICE_META, DeviceMeta } from '../domain/DormLinkDomain';

/** 设备卡片：显示设备状态，支持开关与档位调节 */
@Component
export struct DeviceCard {
  @Prop device: DeviceState;
  onPowerChange: (id: string, power: boolean) => void = () => {};
  onLevelChange: (id: string, level: number) => void = () => {};

  private meta(): DeviceMeta {
    for (let i = 0; i < DEVICE_META.length; i++) {
      if (DEVICE_META[i].kind === this.device.kind) {
        return DEVICE_META[i];
      }
    }
    return DEVICE_META[0];
  }

  build() {
    Column({ space: 8 }) {
      Row() {
        Text(this.meta().symbol).fontSize(22)
        Column({ space: 2 }) {
          Text(this.device.name).fontSize(15).fontWeight(FontWeight.Medium).fontColor('#1A1D26')
          Text(`${this.device.room} · ${this.meta().label}`).fontSize(11).fontColor('#8A90A2')
        }
        .alignItems(HorizontalAlign.Start)
        .layoutWeight(1)
        .margin({ left: 8 })

        Toggle({ type: ToggleType.Switch, isOn: this.device.power })
          .selectedColor('#2F6BFF')
          .onChange((isOn: boolean) => {
            this.onPowerChange(this.device.id, isOn);
          })
      }
      .width('100%')

      Row() {
        Text(this.device.power ? `${this.device.level}%` : '已关闭')
          .fontSize(12)
          .fontColor(this.device.power ? '#2F6BFF' : '#B0B5C3')
        Blank()
        Text(this.meta().unitText).fontSize(11).fontColor('#B0B5C3')
      }
      .width('100%')

      Slider({
        value: this.device.level,
        min: 0,
        max: 100,
        step: 1,
        style: SliderStyle.OutSet
      })
        .selectedColor('#2F6BFF')
        .trackColor('#E7EAF3')
        .enabled(this.device.power)
        .opacity(this.device.power ? 1 : 0.45)
        .onChange((value: number, mode: SliderChangeMode) => {
          this.onLevelChange(this.device.id, Math.round(value));
        })
    }
    .width('100%')
    .padding(12)
    .borderRadius(14)
    .backgroundColor('#FFFFFF')
    .shadow({ radius: 12, color: '#0F1A3D14', offsetY: 4 })
  }
}
