/**
 * 深度嵌套结构测试文件
 */

export class Outer8 {
    middle: Middle8 = new Middle8();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle8 {
    inner: Inner8 = new Inner8();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner8 {
    deeplyNested: DeeplyNested8 = new DeeplyNested8();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested8 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
