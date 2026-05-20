
import { Card } from './Card'

@Component
export struct List {
  @Prop items: string[] = []
  
  build() {
    Column() {
      ForEach(this.items, (item: string) => {
        Card({ title: item })
      })
    }
  }
}
