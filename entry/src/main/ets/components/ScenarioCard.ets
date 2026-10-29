import { Scenario } from '../domain/DormLinkDomain';

/** 场景卡片：一键套用环境并演练 */
@Component
export struct ScenarioCard {
  @Prop scenario: Scenario;
  @Prop activeId: string;
  onRun: (id: string) => void = () => {};

  build() {
    Column({ space: 8 }) {
      Row() {
        Text(this.scenario.name)
          .fontSize(16)
          .fontWeight(FontWeight.Medium)
          .fontColor('#1A1D26')
        Blank()
        if (this.activeId === this.scenario.id) {
          Text('上次演练')
            .fontSize(10)
            .fontColor('#12A594')
            .border({ width: 1, color: '#12A594', radius: 6 })
            .padding({ left: 6, right: 6, top: 1, bottom: 1 })
        }
      }
      .width('100%')

      Text(this.scenario.description)
        .fontSize(12)
        .fontColor('#6B7280')
        .width('100%')

      Row({ space: 12 }) {
        Text(`🌡 ${this.scenario.env.temperature}°C`).fontSize(12).fontColor('#4A5163')
        Text(`💧 ${this.scenario.env.humidity}%`).fontSize(12).fontColor('#4A5163')
        Text(`🔆 ${this.scenario.env.illuminance}lux`).fontSize(12).fontColor('#4A5163')
      }
      .width('100%')

      Button('一键演练')
        .width('100%')
        .height(36)
        .fontSize(14)
        .backgroundColor('#2F6BFF')
        .onClick(() => {
          this.onRun(this.scenario.id);
        })
    }
    .width('100%')
    .padding(14)
    .borderRadius(14)
    .backgroundColor('#FFFFFF')
    .shadow({ radius: 12, color: '#0F1A3D14', offsetY: 4 })
  }
}
