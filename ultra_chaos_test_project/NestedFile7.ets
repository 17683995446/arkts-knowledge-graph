/**
 * 深度嵌套结构测试文件
 */

export class Outer7 {
    middle: Middle7 = new Middle7();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle7 {
    inner: Inner7 = new Inner7();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner7 {
    deeplyNested: DeeplyNested7 = new DeeplyNested7();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested7 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
