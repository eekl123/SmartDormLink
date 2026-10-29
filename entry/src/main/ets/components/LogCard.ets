import { LogEntry } from '../domain/DormLinkDomain';

/** 执行日志卡片：序号、规则、条件、设备变化、冲突说明 */
@Component
export struct LogCard {
  @Prop entry: LogEntry;
  @Prop index: number;

  private timeText(): string {
    const d = new Date(this.entry.at);
    const pad = (n: number): string => n < 10 ? `0${n}` : `${n}`;
    return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }

  build() {
    Column({ space: 6 }) {
      Row({ space: 8 }) {
        Text(`#${this.entry.order}`)
          .fontSize(11)
          .fontColor('#FFFFFF')
          .backgroundColor(this.entry.fired ? '#2F6BFF' : '#98A0B4')
          .borderRadius(6)
          .padding({ left: 6, right: 6, top: 2, bottom: 2 })
        Text(this.entry.ruleName)
          .fontSize(14)
          .fontWeight(FontWeight.Medium)
          .fontColor('#1A1D26')
          .layoutWeight(1)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
        Text(`P${this.entry.priority}`)
          .fontSize(11)
          .fontColor('#8A90A2')
      }
      .width('100%')

      Text(this.timeText()).fontSize(11).fontColor('#A8ADBC').width('100%')

      Text(`条件 ${this.entry.conditionsText}`)
        .fontSize(12)
        .fontColor('#4A5163')
        .width('100%')
        .maxLines(2)

      Text(`变化 ${this.entry.changesText}`)
        .fontSize(12)
        .fontColor(this.entry.fired ? '#12A594' : '#8A90A2')
        .width('100%')
        .maxLines(2)

      if (this.entry.conflictText.length > 0) {
        Text(`冲突 ${this.entry.conflictText}`)
          .fontSize(11)
          .fontColor('#E5484D')
          .width('100%')
          .maxLines(3)
      }
    }
    .width('100%')
    .padding(12)
    .borderRadius(12)
    .backgroundColor('#FFFFFF')
    .opacity(this.index % 2 === 0 ? 1 : 0.98)
  }
}
