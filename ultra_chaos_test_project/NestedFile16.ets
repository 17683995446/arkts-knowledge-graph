/**
 * 深度嵌套结构测试文件
 */

export class Outer16 {
    middle: Middle16 = new Middle16();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle16 {
    inner: Inner16 = new Inner16();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner16 {
    deeplyNested: DeeplyNested16 = new DeeplyNested16();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested16 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
