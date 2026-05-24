/**
 * 装饰器测试文件
 */

@Observed
export class ObservedClass2 {
    @State count: number = 0;
    @Prop title: string = '';
    @Link linkedValue: number = 0;
    
    @StorageProp('key1') storageProp: string = '';
    @StorageLink('key2') storageLink: number = 0;
    
    @Watch('onCountChange')
    @State watchedValue: number = 0;
    
    private onCountChange(): void {
        console.log('count changed');
    }
    
    increment(): void {
        this.count++;
    }
}

@Component
export struct DecoratedComponent2 {
    @BuilderParam content: () => void;
    @Consume('theme') theme: string;
    
    build() {
        Column() {
            this.content()
        }
    }
}
